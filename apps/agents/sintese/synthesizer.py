"""Newsletter synthesizer for SINTESE agent.

Takes scored items and produces a curated newsletter draft in Markdown.
Selects the top items, groups them by category, and generates
summaries and commentary for "Sinal Semanal".
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from apps.agents.sintese.scorer import ScoredItem

logger = logging.getLogger(__name__)

# How many items to include in the newsletter
TOP_ITEMS_COUNT = 18
MIN_SCORE_THRESHOLD = 0.35

# Category definitions for grouping newsletter items
CATEGORIES: dict[str, list[str]] = {
    "AI & Machine Learning": [
        "inteligencia artificial", "machine learning", "llm", "gpt", "claude",
        "deep learning", "ai agent", "generative ai", "ia generativa", "nlp",
    ],
    "Startups & Funding": [
        "startup", "venture capital", "investimento", "rodada", "funding",
        "serie a", "serie b", "seed", "unicornio", "ipo", "aquisicao",
        "fundraising", "acquisition",
    ],
    "Fintech & Pagamentos": [
        "fintech", "pagamento", "credito", "banco digital", "pix",
        "open finance", "drex", "blockchain", "crypto",
    ],
    "Infraestrutura & Dev Tools": [
        "kubernetes", "docker", "aws", "cloud", "microservices", "devops",
        "open source", "api", "database", "python", "typescript", "rust",
        "react", "next.js", "fastapi",
    ],
    "Ecossistema LATAM": [
        "brasil", "brazil", "latam", "america latina", "sao paulo",
        "florianopolis", "agritech", "agtech", "climate tech",
    ],
}


@dataclass
class NewsletterSection:
    """A section of the newsletter with a heading and curated items."""

    heading: str
    items: list[ScoredItem]


def categorize_item(item: ScoredItem) -> str:
    """Assign a single category to a scored item based on keyword matching."""
    text = " ".join([
        item.item.title.lower(),
        (item.item.summary or "").lower(),
        " ".join(item.item.tags),
    ])

    best_category = "Destaque da Semana"
    best_match_count = 0

    for category, keywords in CATEGORIES.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches > best_match_count:
            best_match_count = matches
            best_category = category

    return best_category


def select_top_items(
    scored_items: list[ScoredItem],
    count: int = TOP_ITEMS_COUNT,
    min_score: float = MIN_SCORE_THRESHOLD,
) -> list[ScoredItem]:
    """Select top items ensuring source diversity.

    Limits to max 3 items per source to prevent any single
    feed from dominating the newsletter.
    """
    selected: list[ScoredItem] = []
    source_counts: dict[str, int] = {}
    max_per_source = 3

    for item in scored_items:
        if item.composite_score < min_score:
            continue

        source = item.item.source_name
        current_count = source_counts.get(source, 0)

        if current_count >= max_per_source:
            continue

        selected.append(item)
        source_counts[source] = current_count + 1

        if len(selected) >= count:
            break

    return selected


def group_by_category(items: list[ScoredItem]) -> list[NewsletterSection]:
    """Group selected items into newsletter sections by category."""
    category_items: dict[str, list[ScoredItem]] = {}

    for item in items:
        category = categorize_item(item)
        if category not in category_items:
            category_items[category] = []
        category_items[category].append(item)

    # Sort categories: largest sections first, but "Destaque" always on top
    sections: list[NewsletterSection] = []
    if "Destaque da Semana" in category_items:
        sections.append(NewsletterSection(
            heading="Destaque da Semana",
            items=category_items.pop("Destaque da Semana"),
        ))

    remaining = sorted(
        category_items.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )
    for heading, items in remaining:
        sections.append(NewsletterSection(heading=heading, items=items))

    return sections


def format_item_markdown(item: ScoredItem, index: int) -> str:
    """Format a single newsletter item as Markdown."""
    lines: list[str] = []

    lines.append(f"**{index}. [{item.item.title}]({item.item.url})**")
    lines.append(f"*Fonte: {item.item.source_name}*")

    if item.item.summary:
        # Clean and truncate summary
        summary = item.item.summary.strip()
        # Remove HTML tags if present
        import re
        summary = re.sub(r"<[^>]+>", "", summary)
        if len(summary) > 300:
            summary = summary[:297] + "..."
        lines.append(f"> {summary}")

    lines.append("")
    return "\n".join(lines)


def synthesize_newsletter(
    scored_items: list[ScoredItem],
    edition_number: int = 1,
    edition_date: Optional[datetime] = None,
) -> str:
    """Produce the full newsletter draft in Markdown.

    Args:
        scored_items: All scored items (will be filtered and ranked).
        edition_number: Sequential newsletter edition number.
        edition_date: Date for the newsletter (defaults to now).

    Returns:
        Complete newsletter Markdown ready for review and publication.
    """
    if not edition_date:
        edition_date = datetime.now(timezone.utc)

    date_str = edition_date.strftime("%d/%m/%Y")

    top_items = select_top_items(scored_items)
    sections = group_by_category(top_items)

    lines: list[str] = []

    # Header
    lines.append(f"# Sinal Semanal #{edition_number}")
    lines.append("")
    lines.append(f"*Edicao de {date_str} — Curado pelo agente SINTESE*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Intro
    lines.append(
        f"Esta semana reunimos **{len(top_items)} destaques** do ecossistema "
        f"tech da America Latina e do mundo, selecionados de "
        f"**{len(set(i.item.source_name for i in top_items))} fontes** "
        f"por relevancia para fundadores tecnicos, CTOs e engenheiros seniores."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    item_index = 1
    for section in sections:
        lines.append(f"## {section.heading}")
        lines.append("")

        for scored_item in section.items:
            lines.append(format_item_markdown(scored_item, item_index))
            item_index += 1

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("## Sobre esta edicao")
    lines.append("")
    lines.append(
        "Esta newsletter foi curada pelo **agente SINTESE** da plataforma "
        "[Sinal.lab](https://sinal.ai). O agente analisa mais de 100 fontes "
        "de noticias tech, pontua cada item por relevancia topica, recencia, "
        "autoridade da fonte e relevancia para a America Latina, e seleciona "
        "os destaques da semana."
    )
    lines.append("")
    lines.append(
        "*Inteligencia aberta para quem constroi.*"
    )

    return "\n".join(lines)
