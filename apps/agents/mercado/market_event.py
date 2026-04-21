"""Unified market event for MERCADO v2 editorial analysis.

Wraps heterogeneous signals (funding rounds, new companies, RSS news)
into a single type that the sector classifier, scorer, and synthesizer
can reason about.

Design:
- A MarketEvent is always tied to a company (slug + name).
- event_type discriminates the signal source.
- amount_usd is optional (funding events have it, news/updates may not).
- sector is inferred by the classifier from company + event context.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Optional


@dataclass
class MarketEvent:
    """A single market signal — funding, company update, or news."""

    company_name: str
    company_slug: str
    event_type: str  # "funding_round" | "company_update" | "news"
    occurred_at: date
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    amount_usd: Optional[float] = None  # absolute USD when applicable
    round_type: Optional[str] = None  # funding events only
    title: Optional[str] = None  # display title (e.g. "Plata raises $405M")
    summary: Optional[str] = None  # narrative text
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    investors: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredEvent:
    """A MarketEvent with editorial relevance score."""

    event: MarketEvent
    editorial_score: float  # 0-1, higher = more relevant
    signal_strength: str  # "high" | "medium" | "low"


@dataclass
class SectorSection:
    """A section of the weekly report, focused on one sector."""

    sector_slug: str  # e.g. "fintech", "ai", "devtools"
    heading: str  # display name, e.g. "Fintech & Pagamentos"
    events: list[ScoredEvent]
    narrative: Optional[str] = None  # LLM-generated analysis paragraph
