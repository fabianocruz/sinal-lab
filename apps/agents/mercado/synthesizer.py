"""Content synthesis for MERCADO agent.

Generates Markdown ecosystem snapshot reports from scored company profiles.

When a MercadoWriter is provided, LLM-generated content enriches the report:
  - Ecosystem narrative intro (aggregate trends)
  - Contextual descriptions for top-highlighted companies

Falls back to template-based output when the writer is unavailable or fails.
"""

import logging
from collections import Counter
from typing import TYPE_CHECKING, Optional

from apps.agents.mercado.scorer import ScoredCompanyProfile

if TYPE_CHECKING:
    from apps.agents.mercado.writer import MercadoWriter

logger = logging.getLogger(__name__)


def synthesize_ecosystem_snapshot(
    scored_profiles: list[ScoredCompanyProfile],
    week_number: int,
    writer: Optional["MercadoWriter"] = None,
) -> str:
    """Generate Markdown ecosystem snapshot report.

    Args:
        scored_profiles: List of scored company profiles
        week_number: Week number of the year (1-52)
        writer: Optional LLM writer for editorial content enrichment

    Returns:
        Markdown formatted ecosystem snapshot
    """
    if not scored_profiles:
        return f"""# Ecossistema LATAM — Semana {week_number}/2026

## Status

Sem novas startups descobertas esta semana.
"""

    # Group by city
    by_city: dict[str, list[ScoredCompanyProfile]] = {}
    for scored in scored_profiles:
        city = scored.profile.city or "Cidade não especificada"
        if city not in by_city:
            by_city[city] = []
        by_city[city].append(scored)

    # Group by sector
    by_sector: dict[str, list[ScoredCompanyProfile]] = {}
    for scored in scored_profiles:
        sector = scored.profile.sector or "Outros"
        if sector not in by_sector:
            by_sector[sector] = []
        by_sector[sector].append(scored)

    # Compute top sectors
    sector_counts = Counter(s.profile.sector for s in scored_profiles if s.profile.sector)
    top_sectors = sector_counts.most_common(5)

    # Build report
    report_lines = [
        f"# Ecossistema LATAM — Semana {week_number}/2026",
        "",
        f"## Novas Startups Descobertas: {len(scored_profiles)}",
        "",
    ]

    # Try LLM-generated ecosystem narrative intro
    snapshot_intro = None
    if writer is not None:
        try:
            snapshot_intro = writer.write_snapshot_intro(scored_profiles, week_number)
        except Exception:
            logger.warning("Writer failed to generate snapshot intro", exc_info=True)

    if snapshot_intro:
        report_lines.append(snapshot_intro)
        report_lines.append("")

    # Top 3 highlights (highest confidence)
    highlights = scored_profiles[:3]
    report_lines.append("## Destaques da Semana")
    report_lines.append("")

    # Try LLM-generated highlight descriptions
    highlight_descriptions: Optional[list[str]] = None
    if writer is not None:
        try:
            highlight_descriptions = writer.write_highlight_descriptions(highlights)
        except Exception:
            logger.warning("Writer failed to generate highlight descriptions", exc_info=True)

    for i, scored in enumerate(highlights):
        p = scored.profile
        report_lines.append(f"### {p.name}")

        # Use LLM description if available, otherwise fall back to template
        if highlight_descriptions is not None and i < len(highlight_descriptions):
            report_lines.append(highlight_descriptions[i])
        elif p.description:
            report_lines.append(f"{p.description[:200]}...")

        report_lines.append(f"- **Setor**: {p.sector or 'Não classificado'}")
        report_lines.append(f"- **Local**: {p.city}, {p.country}")
        if p.tech_stack:
            report_lines.append(f"- **Tech Stack**: {', '.join(p.tech_stack[:5])}")
        if p.github_url:
            report_lines.append(f"- **GitHub**: {p.github_url}")
        report_lines.append(
            f"- **Confiança**: {scored.confidence.grade} "
            f"(DQ {scored.confidence.data_quality:.1f}/5, "
            f"AC {scored.confidence.analysis_confidence:.1f}/5)"
        )
        report_lines.append("")

    # Breakdown by sector
    report_lines.append("## Distribuição por Setor")
    report_lines.append("")
    for sector, count in top_sectors:
        report_lines.append(f"- **{sector}**: {count} startups")
    report_lines.append("")

    # Breakdown by city
    report_lines.append("## Mapa por Cidade")
    report_lines.append("")
    for city, profiles in sorted(by_city.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        sector_dist = Counter(s.profile.sector for s in profiles if s.profile.sector)
        top_3_sectors = sector_dist.most_common(3)

        report_lines.append(f"### {city} ({len(profiles)} startups)")
        if top_3_sectors:
            sectors_str = ", ".join(f"{s} ({c})" for s, c in top_3_sectors)
            report_lines.append(f"- **Top Setores**: {sectors_str}")

        # List notable companies (top 3 by confidence)
        notable = sorted(profiles, key=lambda x: x.composite_score, reverse=True)[:3]
        notable_names = [s.profile.name for s in notable]
        report_lines.append(f"- **Notáveis**: {', '.join(notable_names)}")
        report_lines.append("")

    # Editorial mode notice
    use_writer = writer is not None and writer.is_available
    if not use_writer:
        report_lines.append(
            "> *Nota: Este relatorio foi gerado em modo template (sem camada editorial LLM). "
            "As descricoes sao extraidas diretamente das fontes originais. A versao editorial "
            "em portugues requer a configuracao da variavel ANTHROPIC_API_KEY.*"
        )
        report_lines.append("")

    return "\n".join(report_lines)
