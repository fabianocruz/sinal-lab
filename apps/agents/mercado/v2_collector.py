"""MERCADO v2 collector — reads market events from DB + RSS.

Replaces the v1 collector that scraped GitHub orgs. Instead, it queries
existing `funding_rounds` and `companies` tables (populated by FUNDING
and INDEX agents) and enriches with recent sector news via RSS.

Key design:
- MERCADO is now a READER, not a writer of company data.
- Scraping responsibility moved to INDEX (which already covers it).
- Time window: 7 days for primary signal, 90 days for historical context.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from apps.agents.funding.synthesizer import normalize_amount_usd
from apps.agents.mercado.market_event import MarketEvent
from packages.database.models.company import Company
from packages.database.models.funding_round import FundingRound

logger = logging.getLogger(__name__)


def collect_funding_events(
    session: Session,
    days_back: int = 7,
) -> list[MarketEvent]:
    """Load recent funding rounds as market events.

    Args:
        session: SQLAlchemy session.
        days_back: How far back to look (default 7 days for weekly report).

    Returns:
        List of MarketEvent with event_type="funding_round".
    """
    cutoff = date.today() - timedelta(days=days_back)
    rounds = (
        session.query(FundingRound)
        .filter(FundingRound.announced_date >= cutoff)
        .order_by(FundingRound.announced_date.desc())
        .all()
    )

    events: list[MarketEvent] = []
    for r in rounds:
        lead_investors = r.lead_investors or []
        participants = r.participants or []
        investors = lead_investors + [p for p in participants if p not in lead_investors]

        # Normalize amount to absolute USD (handles legacy RSS-in-millions format)
        amount_usd = normalize_amount_usd(r.amount_usd) if r.amount_usd else None

        title = f"{r.company_name} — {_format_round_display(r.round_type)}"
        if amount_usd:
            title = f"{title} ({_format_amount_compact(amount_usd)})"

        events.append(MarketEvent(
            company_name=r.company_name,
            company_slug=r.company_slug,
            event_type="funding_round",
            occurred_at=r.announced_date,
            amount_usd=amount_usd,
            round_type=r.round_type,
            title=title,
            summary=r.notes,
            source_url=r.source_url,
            source_name=r.source_name,
            investors=investors,
            metadata={
                "currency": r.currency,
                "amount_local": r.amount_local,
                "valuation_usd": r.valuation_usd,
                "confidence": r.confidence,
            },
        ))

    logger.info("Collected %d funding events (last %d days)", len(events), days_back)
    return events


def enrich_events_with_companies(
    session: Session,
    events: list[MarketEvent],
) -> list[MarketEvent]:
    """Fill in sector/country/city for events whose company is in the DB.

    Matches on company_slug (case-insensitive).
    """
    if not events:
        return events

    slugs = {e.company_slug.lower() for e in events if e.company_slug}
    if not slugs:
        return events

    companies = (
        session.query(Company)
        .filter(Company.slug.in_(slugs))
        .all()
    )
    by_slug = {c.slug.lower(): c for c in companies}

    enriched = 0
    for event in events:
        c = by_slug.get(event.company_slug.lower())
        if c is None:
            continue
        if not event.sector and c.sector:
            event.sector = c.sector
        if not event.country and c.country:
            event.country = c.country
        if not event.city and c.city:
            event.city = c.city
        enriched += 1

    logger.info("Enriched %d/%d events with company metadata", enriched, len(events))
    return events


def _format_round_display(round_type: Optional[str]) -> str:
    """Human-readable round type."""
    if not round_type:
        return "Rodada"
    mapping = {
        "pre_seed": "Pre-seed",
        "seed": "Seed",
        "series_a": "Série A",
        "series_b": "Série B",
        "series_c": "Série C",
        "series_d": "Série D",
        "series_e": "Série E",
        "series_f": "Série F",
        "series_g": "Série G",
        "venture": "Venture",
        "angel": "Angel",
        "ico": "ICO",
    }
    return mapping.get(round_type, round_type.replace("_", " ").title())


def _format_amount_compact(amount_usd: float) -> str:
    """Compact amount for titles: $405M, $2.3B, $500K."""
    if amount_usd >= 1_000_000_000:
        return f"${amount_usd / 1_000_000_000:.1f}B"
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.1f}M"
    return f"${amount_usd / 1000:.0f}K"
