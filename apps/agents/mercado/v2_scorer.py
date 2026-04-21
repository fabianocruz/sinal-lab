"""MERCADO v2 scorer — editorial relevance per event.

Replaces the v1 scorer (which scored company profiles for discovery).
v2 scores market events (funding rounds, company updates) by how
newsworthy they are for a CTO/VC audience.

Signal weights:
- Round size (large rounds beat small) — 50%
- Source authority (crunchbase > latamlist > manual) — 20%
- Recency (7d beats 30d) — 15%
- Investor signal (Sequoia/a16z/canary/onevc = lift) — 15%
"""

import logging
import math
from datetime import date, timedelta
from typing import Optional

from apps.agents.mercado.market_event import MarketEvent, ScoredEvent, SectorSection

logger = logging.getLogger(__name__)


# Known high-signal investors for LATAM tech
_TIER1_INVESTORS = {
    "sequoia", "a16z", "andreessen horowitz", "tiger global", "softbank",
    "accel", "general catalyst", "founders fund",
}
_TIER2_INVESTORS = {
    "canary", "onevc", "bicycle capital", "valor capital", "monashees",
    "kaszek", "atlantico", "astella", "maya capital", "quona",
}

_SOURCE_AUTHORITY = {
    "crunchbase_manual_dump": 0.9,
    "latamlist": 0.7,
    "neofeed": 0.7,
    "techcrunch": 0.8,
    "sec_form_d": 0.85,
}


def score_event(event: MarketEvent, today: Optional[date] = None) -> ScoredEvent:
    """Return editorial relevance score 0-1 for a single event."""
    today = today or date.today()

    # 1. Round size (log scale: $100M = 0.85, $10M = 0.65, $1M = 0.45, $100K = 0.25)
    size_score = 0.3
    if event.amount_usd:
        if event.amount_usd >= 1_000_000_000:
            size_score = 1.0
        elif event.amount_usd >= 100_000_000:
            size_score = 0.9
        elif event.amount_usd >= 10_000_000:
            size_score = 0.75
        elif event.amount_usd >= 1_000_000:
            size_score = 0.55
        else:
            size_score = 0.35

    # 2. Source authority
    source_score = _SOURCE_AUTHORITY.get((event.source_name or "").lower(), 0.5)

    # 3. Recency
    days_ago = (today - event.occurred_at).days if event.occurred_at else 30
    if days_ago <= 2:
        recency_score = 1.0
    elif days_ago <= 7:
        recency_score = 0.85
    elif days_ago <= 14:
        recency_score = 0.6
    elif days_ago <= 30:
        recency_score = 0.4
    else:
        recency_score = 0.2

    # 4. Investor signal
    investor_score = 0.5
    investor_text = " ".join(event.investors).lower()
    if any(t1 in investor_text for t1 in _TIER1_INVESTORS):
        investor_score = 1.0
    elif any(t2 in investor_text for t2 in _TIER2_INVESTORS):
        investor_score = 0.8

    composite = (
        0.50 * size_score
        + 0.20 * source_score
        + 0.15 * recency_score
        + 0.15 * investor_score
    )

    # Signal strength bucket
    if composite >= 0.75:
        strength = "high"
    elif composite >= 0.55:
        strength = "medium"
    else:
        strength = "low"

    return ScoredEvent(
        event=event,
        editorial_score=round(composite, 3),
        signal_strength=strength,
    )


def score_and_rank_sections(
    sections: list[SectorSection],
    max_events_per_section: int = 5,
    today: Optional[date] = None,
) -> list[SectorSection]:
    """Score events within each section and keep the top N by relevance."""
    for section in sections:
        scored = [score_event(e, today=today) for e in section.events]
        scored.sort(key=lambda s: s.editorial_score, reverse=True)
        section.events = scored[:max_events_per_section]  # type: ignore[assignment]
        logger.debug(
            "Section %s: kept %d/%d events (top score: %.2f)",
            section.sector_slug, len(section.events), len(scored),
            scored[0].editorial_score if scored else 0.0,
        )
    return sections
