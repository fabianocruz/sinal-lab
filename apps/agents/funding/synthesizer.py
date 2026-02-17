"""Markdown report synthesizer for FUNDING agent.

Generates weekly funding reports grouped by round type and amount,
with company details, investors, and confidence scores.
"""

import logging
from typing import TYPE_CHECKING, Optional

from apps.agents.base.llm import strip_html
from apps.agents.funding.scorer import ScoredFundingEvent

if TYPE_CHECKING:
    from apps.agents.funding.writer import FundingWriter

logger = logging.getLogger(__name__)

# Minimum score to include in report
MIN_SCORE_FOR_REPORT = 0.3

# Amount thresholds for grouping (in USD millions)
LARGE_ROUND_THRESHOLD = 5.0  # $5M+


def format_amount(amount_usd: Optional[float]) -> str:
    """Format funding amount in millions USD.

    Args:
        amount_usd: Amount in USD

    Returns:
        Formatted string like "$15.5M" or "Valor não divulgado"
    """
    if amount_usd is None:
        return "Valor não divulgado"

    if amount_usd >= 1.0:
        return f"${amount_usd:.1f}M"
    else:
        # Less than $1M, show in thousands
        return f"${amount_usd * 1000:.0f}K"


def format_round_type(round_type: str) -> str:
    """Format round type for display.

    Args:
        round_type: Normalized round type (e.g., "series_a", "seed")

    Returns:
        Formatted string (e.g., "Série A", "Seed")
    """
    if round_type.startswith("series_"):
        letter = round_type.split("_")[-1].upper()
        return f"Série {letter}"
    elif round_type == "pre_seed":
        return "Pre-Seed"
    elif round_type == "seed":
        return "Seed"
    elif round_type == "ipo":
        return "IPO"
    elif round_type == "debt":
        return "Dívida"
    elif round_type == "grant":
        return "Grant"
    else:
        return round_type.replace("_", " ").title()


def format_confidence_badge(scored_event: ScoredFundingEvent) -> str:
    """Format confidence badge for display.

    Args:
        scored_event: ScoredFundingEvent object

    Returns:
        Formatted string like "A (DQ 4.2/5, AC 4.0/5)"
    """
    conf = scored_event.confidence
    return f"{conf.grade} (DQ {conf.dq_display:.1f}/5, AC {conf.ac_display:.1f}/5)"


def group_by_round_type(
    scored_events: list[ScoredFundingEvent],
) -> dict[str, list[ScoredFundingEvent]]:
    """Group scored events by round type.

    Args:
        scored_events: List of ScoredFundingEvent objects

    Returns:
        Dictionary mapping round type to list of events
    """
    groups: dict[str, list[ScoredFundingEvent]] = {}

    for scored in scored_events:
        round_type = scored.event.round_type
        if round_type not in groups:
            groups[round_type] = []
        groups[round_type].append(scored)

    return groups


def synthesize_funding_report(
    scored_events: list[ScoredFundingEvent],
    week_number: int,
    writer: Optional["FundingWriter"] = None,
) -> str:
    """Generate Markdown funding report grouped by round type.

    When a FundingWriter is provided and available, uses LLM-generated
    content for the intro paragraph and deal highlights. Falls back to
    template-based output when the writer is unavailable or calls fail.

    Args:
        scored_events: List of ScoredFundingEvent objects (sorted by score)
        week_number: Week number of the year
        writer: Optional LLM writer for editorial content

    Returns:
        Markdown report content
    """
    # Filter by minimum score
    filtered = [s for s in scored_events if s.composite_score >= MIN_SCORE_FOR_REPORT]

    if not filtered:
        logger.warning("No funding events meet minimum score threshold (%.2f)", MIN_SCORE_FOR_REPORT)
        return "# Investimentos LATAM — Sem rodadas relevantes esta semana\n\nNenhuma rodada de investimento atingiu o limiar de confiança mínimo."

    logger.info("Synthesizing report for %d funding events", len(filtered))

    # Build report sections
    lines: list[str] = []

    # Header
    lines.append(f"# Investimentos LATAM — Semana {week_number}/2026")
    lines.append("")

    # Try LLM-generated intro, fall back to template
    llm_intro = None
    if writer is not None:
        llm_intro = writer.write_report_intro(filtered, week_number)

    if llm_intro:
        lines.append(llm_intro)
    else:
        lines.append(f"*{len(filtered)} rodadas analisadas de {len(set(s.event.source_name for s in filtered))} fontes.*")
    lines.append("")

    # Top 3 highlights (largest rounds)
    top_3 = sorted(
        [s for s in filtered if s.event.amount_usd is not None],
        key=lambda x: x.event.amount_usd,
        reverse=True,
    )[:3]

    if top_3:
        lines.append("## Destaques da Semana")
        lines.append("")

        # Try LLM-generated deal highlights
        llm_highlights = None
        if writer is not None:
            llm_highlights = writer.write_deal_highlights(top_3)

        for idx, scored in enumerate(top_3):
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            conf_str = format_confidence_badge(scored)

            lines.append(f"### {amount_str} {round_str} — {event.company_name}")

            if event.lead_investors:
                investors_str = ", ".join(event.lead_investors[:3])
                lines.append(f"- **Liderado por**: {investors_str}")

            # Add company_slug as location placeholder (we don't have city in FundingEvent)
            lines.append(f"- **Empresa**: {event.company_slug or 'N/A'}")
            lines.append(f"- **Confiança**: {conf_str}")

            if event.notes and not event.notes.startswith("[AMOUNT_CONFLICT"):
                note_text = strip_html(event.notes, max_length=200)
                lines.append(f"- **Nota**: {note_text}")

            # Add LLM commentary if available
            if llm_highlights and idx < len(llm_highlights):
                lines.append("")
                lines.append(f"> {llm_highlights[idx]}")

            lines.append("")

    # Group by round type
    groups = group_by_round_type(filtered)

    # Series A+ (large rounds)
    large_rounds = [s for s in filtered if s.event.amount_usd and s.event.amount_usd >= LARGE_ROUND_THRESHOLD]
    if large_rounds:
        lines.append(f"## Series A+ (${LARGE_ROUND_THRESHOLD:.0f}M+)")
        lines.append("")

        for scored in large_rounds:
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            conf_str = format_confidence_badge(scored)

            lines.append(f"**{event.company_name}** — {amount_str} {round_str} ({conf_str})")

            if event.lead_investors:
                investors_str = ", ".join(event.lead_investors)
                lines.append(f"  - Investidores: {investors_str}")

            lines.append("")

    # Seed & Pre-Seed
    seed_rounds = [
        s for s in filtered
        if s.event.round_type in ("seed", "pre_seed")
        and (s.event.amount_usd is None or s.event.amount_usd < LARGE_ROUND_THRESHOLD)
    ]
    if seed_rounds:
        lines.append("## Seed & Pre-Seed")
        lines.append("")

        for scored in seed_rounds:
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            conf_str = format_confidence_badge(scored)

            lines.append(f"**{event.company_name}** — {amount_str} {round_str} ({conf_str})")

            if event.lead_investors:
                investors_str = ", ".join(event.lead_investors)
                lines.append(f"  - Investidores: {investors_str}")

            lines.append("")

    # Other rounds
    other_rounds = [
        s for s in filtered
        if s.event.round_type not in ("seed", "pre_seed")
        and (s.event.amount_usd is None or s.event.amount_usd < LARGE_ROUND_THRESHOLD)
    ]
    if other_rounds:
        lines.append("## Outros Investimentos")
        lines.append("")

        for scored in other_rounds:
            event = scored.event
            amount_str = format_amount(event.amount_usd)
            round_str = format_round_type(event.round_type)
            conf_str = format_confidence_badge(scored)

            lines.append(f"**{event.company_name}** — {amount_str} {round_str} ({conf_str})")
            lines.append("")

    # Editorial mode notice
    use_writer = writer is not None and writer.is_available
    if not use_writer:
        lines.append(
            "> *Nota: Este relatorio foi gerado em modo template (sem camada editorial LLM). "
            "As notas sao extraidas diretamente das fontes originais e podem conter "
            "conteudo em ingles ou HTML residual. A versao editorial em portugues requer "
            "a configuracao da variavel ANTHROPIC_API_KEY.*"
        )
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Relatório gerado pelo agente FUNDING — Sinal.lab*")

    return "\n".join(lines)
