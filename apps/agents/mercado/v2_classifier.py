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

# Fallback bucket. Collects two kinds of events:
# 1. events that don't match any specific sector;
# 2. events from sector buckets too thin to earn their own section.
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
    """Build editorial sections from classified events.

    A sector bucket only earns its own section once it has
    ``min_events_per_section`` events — a sector section with a single
    deal reads like filler. Thin buckets are *merged* into the general
    bucket instead of being discarded, so a non-empty input always
    produces at least one non-empty section (a week with one big round
    is still a week with news). Only the ``max_sections`` cap can drop
    events, and it drops the lightest sections first.

    Args:
        events: All collected events.
        max_sections: Maximum sections to include (default 4).
        min_events_per_section: Minimum events for a sector to get its
            own section.

    Returns:
        List of SectorSection, ordered by total editorial weight
        (count + capital). Empty list only when ``events`` is empty.
    """
    if not events:
        return []

    groups = group_by_sector(events)

    # Split buckets into "own section" vs "merge into the general bucket"
    qualifying: dict[str, list[MarketEvent]] = {}
    general_bucket: list[MarketEvent] = list(groups.get(DEFAULT_BUCKET[0], []))

    for slug, bucket_events in groups.items():
        if slug == DEFAULT_BUCKET[0]:
            continue
        if len(bucket_events) >= min_events_per_section:
            qualifying[slug] = bucket_events
        else:
            general_bucket.extend(bucket_events)

    # The general bucket is emitted whenever it has anything in it: a
    # real deal is never worth dropping just because its sector was
    # quiet this week. It still competes for the max_sections slots on
    # weight, so it is the first to be cut on a busy week.
    if general_bucket:
        qualifying[DEFAULT_BUCKET[0]] = general_bucket

    # Map display names
    display_by_slug = {s: d for s, d, _ in EDITORIAL_SECTORS}
    display_by_slug[DEFAULT_BUCKET[0]] = DEFAULT_BUCKET[1]

    # Build sections with scoring
    sections_with_weight: list[tuple[float, SectorSection]] = []
    for slug, bucket_events in qualifying.items():
        # Weight = count + capital proxy ($100M ≈ one extra deal)
        total_usd = sum(e.amount_usd or 0 for e in bucket_events)
        weight = len(bucket_events) + (total_usd / 100_000_000)

        sections_with_weight.append((
            weight,
            SectorSection(
                sector_slug=slug,
                heading=display_by_slug.get(slug, slug.title()),
                events=list(bucket_events),  # type: ignore[arg-type]
            ),
        ))

    # Keep top N by weight
    sections_with_weight.sort(key=lambda x: x[0], reverse=True)
    return [section for _weight, section in sections_with_weight[:max_sections]]
