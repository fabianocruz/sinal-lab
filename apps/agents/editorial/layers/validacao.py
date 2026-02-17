"""Layer 2: VALIDACAO — Data Validation.

Cross-references data quality signals in the agent output.
Flags single-source financial claims, low-confidence data,
and stale information. Assigns data quality grades:
    A: multi-source verified
    B: single-source plausible
    C: unverified — requires human review
    D: contradictory or missing — escalate
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "validacao"

# Confidence thresholds
UNVERIFIED_THRESHOLD = 0.3
LOW_QUALITY_THRESHOLD = 0.5

# Financial claim keywords (Portuguese and English)
FINANCIAL_KEYWORDS = [
    r"\$\s?\d",
    r"US\$",
    r"R\$",
    r"BRL\s?\d",
    r"USD\s?\d",
    r"\d+\s*(milh[oõ]|bilh[oõ]|trilh[oõ]|million|billion|trillion)",
    r"valuation",
    r"valora[cç][aã]o",
    r"funding",
    r"investimento",
    r"rodada\s+(seed|pre-?seed|s[eé]rie)",
    r"series\s+[a-d]",
    r"round\s+[a-d]",
    r"receita",
    r"revenue",
    r"arrecad",
    r"faturamento",
]

# Staleness thresholds (in days)
STALE_THRESHOLD_DAYS = 90
WARNING_STALE_DAYS = 30


def run_validacao(agent_output: AgentOutput) -> LayerResult:
    """Execute the VALIDACAO layer on an AgentOutput.

    Checks:
        1. Data quality score meets minimum thresholds
        2. Financial claims have adequate source backing
        3. Data freshness (flags stale content)
        4. Verification status of the confidence score

    Returns:
        LayerResult with data quality grade.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {}

    dq = agent_output.confidence.data_quality
    ac = agent_output.confidence.analysis_confidence
    source_count = agent_output.confidence.source_count
    verified = agent_output.confidence.verified

    metadata["data_quality"] = dq
    metadata["analysis_confidence"] = ac
    metadata["source_count"] = source_count
    metadata["verified"] = verified

    # --- Check 1: Overall confidence level ---
    if dq < UNVERIFIED_THRESHOLD:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.DATA_QUALITY,
            message=f"Data quality score ({dq}) below unverified threshold ({UNVERIFIED_THRESHOLD})",
            layer=LAYER_NAME,
            detail="Content with DQ < 0.3 is considered unreliable and must not be published without human review",
        ))

    elif dq < LOW_QUALITY_THRESHOLD:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.DATA_QUALITY,
            message=f"Data quality score ({dq}) is low — partially verified",
            layer=LAYER_NAME,
        ))

    # --- Check 2: Financial claims vs source count ---
    has_financial_claims = _detect_financial_claims(agent_output.body_md)
    metadata["financial_claims_detected"] = has_financial_claims

    if has_financial_claims and source_count < 2:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.DATA_QUALITY,
            message="Financial claims detected but only single source — requires multi-source verification",
            layer=LAYER_NAME,
            detail="Per editorial policy, financial data (funding, valuations, revenue) requires at least 2 independent sources for 'verified' status",
        ))
    elif has_financial_claims and not verified:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.DATA_QUALITY,
            message="Financial claims detected with unverified sources",
            layer=LAYER_NAME,
        ))

    # --- Check 3: Data freshness ---
    freshness = _check_freshness(agent_output)
    metadata["data_age_days"] = freshness

    if freshness is not None:
        if freshness > STALE_THRESHOLD_DAYS:
            flags.append(ReviewFlag(
                severity=FlagSeverity.WARNING,
                category=FlagCategory.DATA_QUALITY,
                message=f"Content is {freshness} days old — potentially stale (>{STALE_THRESHOLD_DAYS} days)",
                layer=LAYER_NAME,
            ))
        elif freshness > WARNING_STALE_DAYS:
            flags.append(ReviewFlag(
                severity=FlagSeverity.INFO,
                category=FlagCategory.DATA_QUALITY,
                message=f"Content is {freshness} days old — approaching staleness threshold",
                layer=LAYER_NAME,
            ))

    # --- Check 4: Verification status ---
    if not verified and source_count >= 2:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.DATA_QUALITY,
            message="Multiple sources available but not marked as verified — consider cross-validation",
            layer=LAYER_NAME,
        ))

    # --- Grade assignment ---
    grade = _compute_grade(dq, source_count, verified, flags)

    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)

    logger.info(
        "[%s] Validacao layer: grade=%s, dq=%.3f, sources=%d, flags=%d",
        LAYER_NAME,
        grade,
        dq,
        source_count,
        len(flags),
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=not has_blockers,
        grade=grade,
        flags=flags,
        metadata=metadata,
    )


def _detect_financial_claims(body_md: str) -> bool:
    """Check if the body contains financial claims."""
    if not body_md:
        return False
    text = body_md.lower()
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in FINANCIAL_KEYWORDS)


def _check_freshness(output: AgentOutput) -> Optional[int]:
    """Return age of content in days, or None if unknown."""
    if output.generated_at:
        delta = datetime.now(timezone.utc) - output.generated_at
        return max(0, delta.days)
    return None


def _compute_grade(
    dq: float,
    source_count: int,
    verified: bool,
    flags: list[ReviewFlag],
) -> str:
    """Compute data quality grade per editorial policy.

    A: multi-source verified (DQ >= 0.7, sources >= 3, verified)
    B: single-source plausible (DQ >= 0.5, sources >= 1)
    C: unverified — needs human review (DQ >= 0.3)
    D: contradictory or missing (DQ < 0.3 or blockers)
    """
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)

    if has_blockers or dq < UNVERIFIED_THRESHOLD:
        return "D"

    if dq >= 0.7 and source_count >= 3 and verified:
        return "A"

    if dq >= 0.5 and source_count >= 1:
        return "B"

    return "C"
