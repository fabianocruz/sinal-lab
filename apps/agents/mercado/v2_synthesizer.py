"""MERCADO v2 synthesizer — Markdown report generation.

Takes scored SectorSections and renders a SINTESE-style newsletter
with intro, per-sector analysis, callouts, and source attribution.
"""

import logging
from typing import Optional

from apps.agents.mercado.market_event import SectorSection
from apps.agents.mercado.v2_writer import MercadoV2Writer, EditorialMetadata

logger = logging.getLogger(__name__)


def synthesize_market_intel(
    sections: list[SectorSection],
    week_number: int,
    writer: Optional[MercadoV2Writer] = None,
) -> tuple[str, Optional[EditorialMetadata]]:
    """Generate Markdown body + editorial metadata.

    Returns:
        (body_md, editorial_metadata). metadata is None if writer unavailable.
    """
    if not sections:
        return _empty_report(week_number), None

    lines: list[str] = [
        f"# Market Intelligence LATAM — Semana {week_number}/2026",
        "",
        "---",
        "",
    ]

    # 1. Intro (LLM thesis of the week)
    intro: Optional[str] = None
    if writer:
        try:
            intro = writer.write_intro(sections, week_number)
        except Exception:
            logger.warning("Intro generation failed", exc_info=True)

    if intro:
        lines.append(intro)
    else:
        # Fallback: template intro
        total_events = sum(len(s.events) for s in sections)
        total_usd = sum(
            getattr(e, "event", e).amount_usd or 0
            for s in sections for e in s.events
        )
        amount_str = _format_compact(total_usd) if total_usd else "volume nao divulgado"
        lines.append(
            f"Semana {week_number} registrou {total_events} movimentos relevantes "
            f"no ecossistema tech LATAM, somando {amount_str}. A edicao cobre "
            f"{len(sections)} setores com maior densidade de sinal."
        )
    lines.extend(["", "---", ""])

    # 2. Editorial metadata (callouts + topics)
    editorial_meta: Optional[EditorialMetadata] = None
    if writer:
        try:
            editorial_meta = writer.write_editorial_metadata(sections, week_number)
        except Exception:
            logger.warning("Editorial metadata generation failed", exc_info=True)

    # 3. Per-sector sections
    for section in sections:
        lines.append(f"## {section.heading}")
        lines.append("")

        # LLM analysis
        analysis: Optional[str] = None
        if writer:
            try:
                analysis = writer.write_sector_analysis(section, week_number)
                section.narrative = analysis
            except Exception:
                logger.warning("Section analysis failed for %s", section.sector_slug)

        if analysis:
            lines.append(analysis)
            lines.append("")

        # Event list (compact, always present as evidence)
        lines.append("**Movimentos da semana:**")
        lines.append("")
        for scored in section.events:
            e = scored.event if hasattr(scored, "event") else scored
            amount = _format_compact(e.amount_usd) if e.amount_usd else "valor nao divulgado"
            location = ", ".join(filter(None, [e.city, e.country])) or "LATAM"
            investors = f" — liderada por {', '.join(e.investors[:2])}" if e.investors else ""
            line = f"- **{e.company_name}** ({location}): {e.round_type or e.event_type} {amount}{investors}."
            if e.source_url:
                line += f" [Fonte]({e.source_url})"
            lines.append(line)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Gerado por Valentina Rojas (MERCADO) — Sinal.lab.*")

    return "\n".join(lines), editorial_meta


def _empty_report(week_number: int) -> str:
    return (
        f"# Market Intelligence LATAM — Semana {week_number}/2026\n\n"
        f"---\n\n"
        f"Semana sem volume suficiente para analise editorial. "
        f"Proxima edicao quando o sinal retornar.\n"
    )


def _format_compact(amount_usd: Optional[float]) -> str:
    if not amount_usd:
        return ""
    if amount_usd >= 1_000_000_000:
        return f"${amount_usd / 1_000_000_000:.1f}B"
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.1f}M"
    return f"${amount_usd / 1000:.0f}K"
