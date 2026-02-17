"""Database persistence for FUNDING agent.

Handles FundingRound upsert logic with confidence-based merging
and Company metadata updates.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.agents.funding.collector import FundingEvent
from packages.database.models.company import Company
from packages.database.models.funding_round import FundingRound

logger = logging.getLogger(__name__)


def upsert_funding_round(
    session: Session,
    event: FundingEvent,
    confidence: float,
) -> FundingRound:
    """Insert or update a funding round record.

    Logic:
    - Check if exists by (company_slug, round_type, announced_date)
    - If exists and new confidence > old confidence: update
    - Else: insert new record

    Args:
        session: SQLAlchemy session
        event: FundingEvent to persist
        confidence: Confidence score (0-1)

    Returns:
        FundingRound record (existing or new)
    """
    if not event.company_slug:
        logger.warning("Cannot persist funding event without company_slug: %s", event.company_name)
        # Still create a record with company_name as fallback
        # In production, this should trigger a warning to admin

    # Check if exists
    existing = None
    if event.company_slug and event.announced_date:
        existing = (
            session.query(FundingRound)
            .filter_by(
                company_slug=event.company_slug,
                round_type=event.round_type,
                announced_date=event.announced_date,
            )
            .first()
        )

    if existing:
        # Update only if new confidence > old
        if confidence > existing.confidence:
            logger.info(
                "Updating funding round for %s (confidence: %.2f -> %.2f)",
                event.company_name,
                existing.confidence,
                confidence,
            )

            existing.amount_usd = event.amount_usd
            existing.amount_local = event.amount_local
            existing.currency = event.currency
            existing.valuation_usd = event.valuation_usd
            existing.lead_investors = event.lead_investors
            existing.participants = event.participants
            existing.source_url = event.source_url
            existing.source_name = event.source_name
            existing.confidence = confidence
            existing.notes = event.notes
            existing.updated_at = datetime.now(timezone.utc)

            session.commit()
            return existing
        else:
            logger.debug(
                "Skipping update for %s (existing confidence %.2f >= new %.2f)",
                event.company_name,
                existing.confidence,
                confidence,
            )
            return existing

    # Insert new record
    funding_round = FundingRound(
        id=uuid4(),
        company_slug=event.company_slug or event.company_name.lower().replace(" ", "-"),
        company_name=event.company_name,
        round_type=event.round_type,
        amount_usd=event.amount_usd,
        amount_local=event.amount_local,
        currency=event.currency,
        valuation_usd=event.valuation_usd,
        announced_date=event.announced_date,
        closed_date=None,  # Not available from RSS feeds
        lead_investors=event.lead_investors,
        participants=event.participants,
        source_url=event.source_url,
        source_name=event.source_name,
        confidence=confidence,
        notes=event.notes,
    )

    session.add(funding_round)
    session.commit()

    logger.info(
        "Inserted new funding round: %s %s (%.2f confidence)",
        event.company_name,
        event.round_type,
        confidence,
    )

    return funding_round


def update_company_funding_stats(
    session: Session,
    company_slug: str,
) -> None:
    """Update Company metadata with funding statistics.

    Updates:
    - last_funding_date
    - total_raised_usd (sum of all rounds)

    Args:
        session: SQLAlchemy session
        company_slug: Company slug to update
    """
    # Get company
    company = session.query(Company).filter_by(slug=company_slug).first()
    if not company:
        logger.warning("Company %s not found, cannot update funding stats", company_slug)
        return

    # Get all funding rounds for this company
    rounds = session.query(FundingRound).filter_by(company_slug=company_slug).all()

    if not rounds:
        return

    # Compute stats
    latest_date = max(r.announced_date for r in rounds if r.announced_date)
    total_raised = sum(r.amount_usd for r in rounds if r.amount_usd)

    # Update company metadata
    if not company.metadata_:
        company.metadata_ = {}

    company.metadata_["last_funding_date"] = latest_date.isoformat() if latest_date else None
    company.metadata_["total_raised_usd"] = round(total_raised, 2) if total_raised > 0 else None
    company.metadata_["funding_rounds_count"] = len(rounds)
    company.updated_at = datetime.now(timezone.utc)

    session.commit()

    logger.info(
        "Updated company %s: last_funding_date=%s, total_raised=$%.2fM",
        company_slug,
        latest_date,
        total_raised,
    )


def persist_all_events(
    session: Session,
    events: list[tuple[FundingEvent, float]],
) -> dict[str, int]:
    """Persist all funding events to database.

    Args:
        session: SQLAlchemy session
        events: List of (FundingEvent, confidence) tuples

    Returns:
        Dictionary with stats: {\"inserted\": X, \"updated\": Y, \"skipped\": Z}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    for event, confidence in events:
        # Get existing record count before upsert
        existing_count = (
            session.query(FundingRound)
            .filter_by(
                company_slug=event.company_slug,
                round_type=event.round_type,
                announced_date=event.announced_date,
            )
            .count()
        )

        # Upsert
        result = upsert_funding_round(session, event, confidence)

        # Update stats
        if existing_count == 0:
            stats["inserted"] += 1
        elif result.confidence == confidence:
            stats["updated"] += 1
        else:
            stats["skipped"] += 1

        # Update company stats if company exists
        if event.company_slug:
            update_company_funding_stats(session, event.company_slug)

    logger.info(
        "Persistence complete: %d inserted, %d updated, %d skipped",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
    )

    return stats
