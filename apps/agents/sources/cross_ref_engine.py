"""Cross-reference engine for multi-source claim verification.

Compares claims (e.g., "Nubank raised $750M Series G") against independent
data sources to determine confirmation status and adjust confidence scores.
Uses fuzzy entity matching (SequenceMatcher, threshold 0.85) consistent
with entity_resolver.py.

Pure functions only -- no HTTP calls. All source data must be pre-fetched
and passed in as dicts.

Falls back gracefully: unmatched claims are tagged UNCONFIRMED with zero
confidence delta (no penalty, no boost).

Usage:
    from apps.agents.sources.cross_ref_engine import (
        Claim,
        CrossRefResult,
        ConfirmationStatus,
        cross_reference_claim,
        cross_reference_batch,
        build_claim_from_funding_event,
        build_claim_from_authorization,
    )

    claim = build_claim_from_funding_event({
        "company_name": "Nubank",
        "round_type": "Series G",
        "amount_usd": 750_000_000,
        "source_url": "https://example.com",
        "source_name": "Crunchbase",
    })
    result = cross_reference_claim(claim, available_sources)
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Dict, List, Optional

from apps.agents.sources.dedup import compute_composite_hash

logger = logging.getLogger(__name__)

# Fuzzy matching threshold -- same as entity_resolver.py (0.85)
_ENTITY_MATCH_THRESHOLD = 0.85

# Confidence adjustments per source
_CONFIDENCE_BOOST_PER_CONFIRMATION = 0.1
_CONFIDENCE_PENALTY_PER_CONTRADICTION = 0.15

# Maximum relative difference in amounts before flagging contradiction
_AMOUNT_CONTRADICTION_THRESHOLD = 0.30


@dataclass
class Claim:
    """A verifiable claim extracted from a data source.

    Content hash is auto-computed from entity_name + claim_type to enable
    deduplication of equivalent claims from different sources.
    """

    text: str
    claim_type: str
    entity_name: str
    source_items: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = compute_composite_hash(
                self.entity_name.lower().strip(), self.claim_type
            )


class ConfirmationStatus(str, Enum):
    """Result of cross-referencing a claim against independent sources.

    CONFIRMED: 2+ independent sources agree.
    PARTIALLY_CONFIRMED: 1 independent source agrees.
    UNCONFIRMED: No matching sources found.
    CONTRADICTED: At least one source provides conflicting data
                  with no confirmations.
    """

    CONFIRMED = "confirmed"
    PARTIALLY_CONFIRMED = "partially_confirmed"
    UNCONFIRMED = "unconfirmed"
    CONTRADICTED = "contradicted"


@dataclass
class CrossRefResult:
    """Outcome of cross-referencing a single claim."""

    claim: Claim
    status: ConfirmationStatus
    confirmation_count: int
    confirming_sources: List[str]
    conflicting_sources: List[str] = field(default_factory=list)
    confidence_delta: float = 0.0


def _entity_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two entity names.

    Uses SequenceMatcher consistent with entity_resolver.py.

    Args:
        a: First entity name.
        b: Second entity name.

    Returns:
        Float between 0.0 and 1.0 indicating similarity.
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def cross_reference_claim(
    claim: Claim,
    available_sources: List[Dict[str, Any]],
) -> CrossRefResult:
    """Cross-reference a single claim against available source data.

    Pure function -- no HTTP calls. Each item in available_sources must
    have at minimum ``source_name`` and ``entity_name`` keys. Optionally
    includes ``amount`` for funding-type contradiction detection.

    Args:
        claim: The claim to verify.
        available_sources: List of dicts with source data to check against.

    Returns:
        CrossRefResult with confirmation status and confidence delta.
    """
    confirming: List[str] = []
    conflicting: List[str] = []

    for source in available_sources:
        source_entity = source.get("entity_name", "")
        source_name = source.get("source_name", "unknown")

        # Check if entity names match (fuzzy)
        similarity = _entity_similarity(claim.entity_name, source_entity)
        if similarity < _ENTITY_MATCH_THRESHOLD:
            continue

        # Entity matched -- check for amount contradiction
        claim_amount = claim.metadata.get("amount")
        source_amount = source.get("amount")

        if (
            claim_amount is not None
            and source_amount is not None
        ):
            max_val = max(abs(claim_amount), abs(source_amount))
            if max_val > 0:
                diff_ratio = abs(claim_amount - source_amount) / max_val
                if diff_ratio > _AMOUNT_CONTRADICTION_THRESHOLD:
                    conflicting.append(source_name)
                    continue

        # Entity matches and no contradiction detected
        confirming.append(source_name)

    # Determine status
    if len(confirming) == 0 and len(conflicting) > 0:
        status = ConfirmationStatus.CONTRADICTED
    elif len(confirming) == 0:
        status = ConfirmationStatus.UNCONFIRMED
    elif len(confirming) == 1:
        status = ConfirmationStatus.PARTIALLY_CONFIRMED
    else:
        status = ConfirmationStatus.CONFIRMED

    # Compute confidence delta
    delta = (
        len(confirming) * _CONFIDENCE_BOOST_PER_CONFIRMATION
        - len(conflicting) * _CONFIDENCE_PENALTY_PER_CONTRADICTION
    )

    return CrossRefResult(
        claim=claim,
        status=status,
        confirmation_count=len(confirming),
        confirming_sources=confirming,
        conflicting_sources=conflicting,
        confidence_delta=delta,
    )


def cross_reference_batch(
    claims: List[Claim],
    available_sources: List[Dict[str, Any]],
) -> List[CrossRefResult]:
    """Cross-reference multiple claims against available sources.

    Convenience wrapper that calls cross_reference_claim for each claim.

    Args:
        claims: List of claims to verify.
        available_sources: List of dicts with source data to check against.

    Returns:
        List of CrossRefResult, one per claim, in the same order.
    """
    return [
        cross_reference_claim(claim, available_sources)
        for claim in claims
    ]


def build_claim_from_funding_event(event: Dict[str, Any]) -> Claim:
    """Build a Claim from a funding event dictionary.

    Args:
        event: Dict with keys: company_name, round_type, amount_usd,
               source_url, source_name.

    Returns:
        Claim with claim_type="funding_round".
    """
    company_name = event.get("company_name", "")
    round_type = event.get("round_type", "")
    amount_usd = event.get("amount_usd")
    source_url = event.get("source_url", "")
    source_name = event.get("source_name", "")

    if amount_usd is not None:
        amount_display = f"${amount_usd:,.0f}"
    else:
        amount_display = "undisclosed amount"

    return Claim(
        text=f"{company_name} raised {amount_display} in {round_type}",
        claim_type="funding_round",
        entity_name=company_name,
        source_items=[{"source_name": source_name, "source_url": source_url}],
        metadata={"amount": amount_usd, "round_type": round_type},
    )


def build_claim_from_authorization(institution: Dict[str, Any]) -> Claim:
    """Build a Claim from a BCB authorization dictionary.

    Args:
        institution: Dict with keys: name, cnpj, segment, authorization_date.

    Returns:
        Claim with claim_type="authorization".
    """
    name = institution.get("name", "")
    cnpj = institution.get("cnpj", "")
    segment = institution.get("segment", "")
    authorization_date = institution.get("authorization_date", "")

    return Claim(
        text=f"{name} authorized by BCB as {segment}",
        claim_type="authorization",
        entity_name=name,
        source_items=[{"source_name": "BCB", "entity_name": name}],
        metadata={
            "cnpj": cnpj,
            "segment": segment,
            "authorization_date": authorization_date,
        },
    )
