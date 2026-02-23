"""Newsletter synthesizer for SINTESE agent.

Takes scored items and produces a curated newsletter draft in Markdown.
Selects the top items, groups them by category, and generates
summaries and commentary for "Sinal Semanal".
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from apps.agents.base.persona_registry import get_display_name
from apps.agents.sintese.scorer import ScoredItem

if TYPE_CHECKING:
    from apps.agents.sintese.writer import SinteseWriter

logger = logging.getLogger(__name__)

# How many items to include in the newsletter
TOP_ITEMS_COUNT = 18
MIN_SCORE_THRESHOLD = 0.35

# Category definitions for grouping newsletter items (aligned with Editorial v2)
CATEGORIES: dict[str, list[str]] = {
    "AI & Infraestrutura Inteligente": [
        "inteligencia artificial", "machine learning", "llm", "gpt", "claude",
        "deep learning", "ai agent", "generative ai", "ia generativa", "nlp",
        "agentic ai", "foundation model", "fine-tuning", "rag", "mlops",
        "inference", "ai governance",
    ],
    "Fintech & Infraestrutura Financeira": [
        "fintech", "pagamento", "credito", "banco digital", "pix",
        "open finance", "drex", "blockchain", "crypto", "stablecoin",
        "tokenização", "embedded finance", "neobank", "remessa",
        "cross-border", "defi",
    ],
    "Engenharia & Plataforma": [
        "kubernetes", "docker", "aws", "cloud", "microservices", "devops",
        "open source", "api", "database", "python", "typescript", "rust",
        "react", "next.js", "fastapi", "observability", "sre",
    ],
    "Venture Capital & Ecossistema": [
        "startup", "venture capital", "investimento", "rodada", "funding",
        "serie a", "serie b", "seed", "unicornio", "ipo", "aquisicao",
        "fundraising", "acquisition", "agritech", "agtech", "climate tech",
        "ecosystem", "latam", "america latina",
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


def format_item_markdown(
    item: ScoredItem,
    index: int,
    summary_override: Optional[str] = None,
) -> str:
    """Format a single newsletter item as Markdown.

    Args:
        item: The scored item to format.
        index: The item number in the newsletter.
        summary_override: If provided, use this instead of the RSS summary.
    """
    lines: list[str] = []

    lines.append(f"**{index}. [{item.item.title}]({item.item.url})**")
    lines.append(f"*Fonte: {item.item.source_name}*")

    summary = summary_override
    if summary is None and item.item.summary:
        # Clean and truncate RSS summary
        summary = item.item.summary.strip()
        import re
        summary = re.sub(r"<[^>]+>", "", summary)
        if len(summary) > 300:
            summary = summary[:297] + "..."

    if summary:
        lines.append(f"> {summary}")

    if item.item.image_url:
        lines.append("")
        lines.append(f"![{item.item.title}]({item.item.image_url})")

    if item.item.video_url:
        lines.append("")
        lines.append(f"[▶ Assistir video]({item.item.video_url})")

    lines.append("")
    return "\n".join(lines)


def synthesize_newsletter(
    scored_items: list[ScoredItem],
    edition_number: int = 1,
    edition_date: Optional[datetime] = None,
    writer: Optional["SinteseWriter"] = None,
) -> tuple[str, list[NewsletterSection]]:
    """Produce the full newsletter draft in Markdown.

    When a writer is provided and available, generates LLM-powered editorial
    content (intro paragraph, section commentary, rewritten summaries).
    Falls back to template-based output per-piece when the LLM is unavailable
    or returns None.

    Args:
        scored_items: All scored items (will be filtered and ranked).
        edition_number: Sequential newsletter edition number.
        edition_date: Date for the newsletter (defaults to now).
        writer: Optional LLM editorial writer for enhanced content.

    Returns:
        Tuple of (newsletter Markdown, list of sections used).
    """
    if not edition_date:
        edition_date = datetime.now(timezone.utc)

    date_str = edition_date.strftime("%d/%m/%Y")

    top_items = select_top_items(scored_items)
    sections = group_by_category(top_items)

    use_writer = writer is not None and writer.is_available

    lines: list[str] = []

    # Header
    lines.append(f"# Sinal Semanal #{edition_number}")
    lines.append("")
    persona_name = get_display_name("sintese")
    lines.append(f"*Edicao de {date_str} — Curado por {persona_name} (SINTESE)*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Intro: try LLM, fallback to template
    llm_intro = None
    if use_writer:
        llm_intro = writer.write_newsletter_intro(sections, edition_number)

    if llm_intro:
        lines.append(llm_intro)
    else:
        lines.append(
            f"Esta semana reunimos **{len(top_items)} destaques** do ecossistema "
            f"tech da America Latina e do mundo, selecionados de "
            f"**{len(set(i.item.source_name for i in top_items))} fontes** "
            f"por relevancia para fundadores tecnicos, CTOs e engenheiros seniores."
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections: try LLM per section, fallback to template
    item_index = 1
    for section in sections:
        lines.append(f"## {section.heading}")
        lines.append("")

        section_content = None
        if use_writer:
            section_content = writer.write_section_content(section)

        if section_content:
            # LLM editorial commentary
            lines.append(section_content.intro)
            lines.append("")
            for i, scored_item in enumerate(section.items):
                lines.append(format_item_markdown(
                    scored_item, item_index,
                    summary_override=section_content.summaries[i],
                ))
                item_index += 1
        else:
            # Template fallback
            for scored_item in section.items:
                lines.append(format_item_markdown(scored_item, item_index))
                item_index += 1

        lines.append("---")
        lines.append("")

    # Footer
    persona_footer = get_display_name("sintese")
    lines.append("## Sobre esta edicao")
    lines.append("")
    lines.append(
        f"Esta newsletter foi curada por **{persona_footer}** na plataforma "
        "[Sinal.lab](https://sinal.ai). O pipeline analisa mais de 100 fontes "
        "de noticias tech, pontua cada item por relevancia topica, recencia, "
        "autoridade da fonte e relevancia para a America Latina, e seleciona "
        "os destaques da semana."
    )
    lines.append("")
    lines.append(
        "*Inteligencia aberta para quem constroi.*"
    )

    return "\n".join(lines), sections
