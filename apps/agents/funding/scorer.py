"""Confidence scoring for FUNDING agent.

Scores funding events based on source count, amount verification,
data freshness, and source reliability.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.funding.collector import FundingEvent

logger = logging.getLogger(__name__)


@dataclass
class ScoredFundingEvent:
    """A funding event with confidence score.

    Combines the raw FundingEvent with a computed ConfidenceScore
    for ranking and filtering.
    """

    event: FundingEvent
    confidence: ConfidenceScore
    composite_score: float  # For sorting

    def __post_init__(self) -> None:
        """Compute composite score from confidence."""
        self.composite_score = self.confidence.composite


def score_single_event(event: FundingEvent, today: date) -> ScoredFundingEvent:
    """Score a single funding event based on multiple signals.

    Confidence signals:
    - Amount verified across sources (from notes)
    - Has API source vs RSS-only
    - Data freshness (days since announcement)
    - Amount completeness (has amount vs missing)

    Args:
        event: FundingEvent to score
        today: Current date for freshness calculation

    Returns:
        ScoredFundingEvent with confidence score
    """
    # Detect if amount conflict flag is present
    amount_verified = False
    has_conflict = False
    if event.notes and "AMOUNT_CONFLICT" in event.notes:
        has_conflict = True
    else:
        # No conflict means amount is verified if present
        amount_verified = event.amount_usd is not None

    # Detect if API source (for MVP, all sources are RSS)
    # This would be True if source_name contains "api" or "dealroom"
    has_api_source = "api" in event.source_name.lower() or "dealroom" in event.source_name.lower()

    # Calculate freshness
    data_freshness_days = 999  # Default: very old
    if event.announced_date:
        delta = today - event.announced_date
        data_freshness_days = delta.days

    # Source count (hardcoded to 1 for MVP, will be inferred from merger in future)
    source_count = 1

    # Compute base confidence
    confidence = compute_confidence(
        source_count=source_count,
        sources_verified=1 if amount_verified else 0,
        data_freshness_days=data_freshness_days,
    )

    # Adjust DQ based on funding-specific signals
    dq = confidence.data_quality

    # Penalty for amount conflict
    if has_conflict:
        dq *= 0.7
        logger.debug("Amount conflict penalty for %s: DQ reduced to %.2f", event.company_name, dq)

    # Bonus for API source
    if has_api_source:
        dq = min(dq * 1.2, 1.0)

    # Penalty for missing amount
    if event.amount_usd is None:
        dq *= 0.8
        logger.debug("Missing amount penalty for %s: DQ reduced to %.2f", event.company_name, dq)

    # Recalculate confidence with adjusted DQ
    confidence = ConfidenceScore(
        data_quality=dq,
        analysis_confidence=min(dq * 0.9, 0.95),
        source_count=source_count,
        verified=amount_verified,
    )

    return ScoredFundingEvent(
        event=event,
        confidence=confidence,
        composite_score=confidence.composite,
    )


def score_events(events: list[FundingEvent]) -> list[ScoredFundingEvent]:
    """Score all funding events and sort by composite score.

    Args:
        events: List of processed FundingEvent objects

    Returns:
        List of ScoredFundingEvent objects, sorted descending by score
    """
    today = date.today()

    scored: list[ScoredFundingEvent] = []
    for event in events:
        scored_event = score_single_event(event, today)
        scored.append(scored_event)

    # Sort by composite score (highest first)
    scored.sort(key=lambda x: x.composite_score, reverse=True)

    logger.info(
        "Scored %d funding events. Top score: %.3f, Bottom score: %.3f",
        len(scored),
        scored[0].composite_score if scored else 0,
        scored[-1].composite_score if scored else 0,
    )

    return scored
