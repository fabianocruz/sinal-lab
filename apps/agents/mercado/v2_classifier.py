"""MERCADO v2 classifier — maps events into editorial sector buckets.

The editorial line organizes the weekly report around 4-5 fixed buckets,
with a rotating "vertical of the quarter" slot. This classifier normalizes
the raw `sector` field (which may be None, "DevTools", "Fintech", etc.)
into the editorial taxonomy.
"""

import logging
from collections import defaultdict
from typing import Optional

from apps.agents.mercado.market_event import MarketEvent, SectorSection

logger = logging.getLogger(__name__)


# Editorial buckets for the weekly report.
# Order matters: events match the FIRST bucket that claims them.
EDITORIAL_SECTORS: list[tuple[str, str, list[str]]] = [
    # (slug, display_name, matching_keywords_lowercase)
    (
        "fintech",
        "Fintech & Infraestrutura Financeira",
        ["fintech", "finance", "financeira", "banco", "bank", "payments", "pagamentos",
         "credit", "credito", "crédito", "lending", "neobank", "embedded finance",
         "open finance", "crypto", "cripto", "blockchain", "bitcoin", "stablecoin",
         "insurtech", "seguros"],
    ),
    (
        "ai",
        "AI & Infraestrutura Inteligente",
        ["ai", "artificial intelligence", "inteligência artificial", "machine learning",
         "ml", "deep learning", "llm", "generative", "agents", "agentes", "data science",
         "analytics"],
    ),
    (
        "devtools",
        "DevTools & Engenharia",
        ["devtools", "developer tools", "saas", "platform", "plataforma", "infrastructure",
         "infraestrutura", "cloud", "api", "sdk", "observability", "observabilidade",
         "cybersecurity", "segurança", "security"],
    ),
    (
        "commerce",
        "Commerce & Marketplace",
        ["e-commerce", "ecommerce", "commerce", "marketplace", "retail", "logistics",
         "logística", "supply chain", "delivery"],
    ),
    (
        "vertical",
        "Verticais em Alta",
        ["healthtech", "health", "saúde", "edtech", "education", "educação",
         "proptech", "real estate", "agritech", "agriculture", "cleantech",
         "mobility", "mobilidade", "hrtech", "legaltech"],
    ),
]

# Fallback bucket for events that don't match any specific sector
DEFAULT_BUCKET = ("cross", "Sinais Gerais do Ecossistema", [])


def classify_event(event: MarketEvent) -> str:
    """Return the editorial sector slug for an event.

    Uses event.sector + title + summary + company_slug as signal.
    """
    haystack = " ".join(filter(None, [
        event.sector or "",
        event.title or "",
        event.summary or "",
        event.company_slug or "",
    ])).lower()

    for slug, _display, keywords in EDITORIAL_SECTORS:
        if any(kw in haystack for kw in keywords):
            return slug

    return DEFAULT_BUCKET[0]


def group_by_sector(events: list[MarketEvent]) -> dict[str, list[MarketEvent]]:
    """Group events by their editorial sector slug."""
    groups: dict[str, list[MarketEvent]] = defaultdict(list)
    for event in events:
        slug = classify_event(event)
        groups[slug].append(event)
    return dict(groups)


def build_sections(
    events: list[MarketEvent],
    max_sections: int = 4,
    min_events_per_section: int = 2,
) -> list[SectorSection]:
    """Build editorial sections, dropping buckets with too few events.

    Args:
        events: All collected events.
        max_sections: Maximum sections to include (default 4).
        min_events_per_section: Minimum events per section to include it.

    Returns:
        List of SectorSection, ordered by total editorial weight
        (sum of amount_usd + count).
    """
    groups = group_by_sector(events)

    # Map display names
    display_by_slug = {s: d for s, d, _ in EDITORIAL_SECTORS}
    display_by_slug[DEFAULT_BUCKET[0]] = DEFAULT_BUCKET[1]

    # Build sections with scoring
    sections_with_weight: list[tuple[float, SectorSection]] = []
    for slug, bucket_events in groups.items():
        if len(bucket_events) < min_events_per_section:
            continue
        # Weight = count + log of total capital (rough proxy)
        total_usd = sum(e.amount_usd or 0 for e in bucket_events)
        weight = len(bucket_events) + (total_usd / 100_000_000)

        section = SectorSection(
            sector_slug=slug,
            heading=display_by_slug.get(slug, slug.title()),
            events=[],  # populated by scorer
        )
        sections_with_weight.append((weight, section))

    # Keep top N by weight
    sections_with_weight.sort(key=lambda x: x[0], reverse=True)
    top = [s for _w, s in sections_with_weight[:max_sections]]

    # Attach raw events back (scorer will score + filter per section)
    for section in top:
        section.events = [e for e in groups[section.sector_slug]]  # type: ignore[assignment]

    return top
