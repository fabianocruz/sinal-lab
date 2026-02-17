"""Content synthesis for MERCADO agent.

Generates Markdown ecosystem snapshot reports from scored company profiles.
"""

import logging
from collections import Counter

from apps.agents.mercado.scorer import ScoredCompanyProfile

logger = logging.getLogger(__name__)


def synthesize_ecosystem_snapshot(
    scored_profiles: list[ScoredCompanyProfile],
    week_number: int,
) -> str:
    """Generate Markdown ecosystem snapshot report.

    Args:
        scored_profiles: List of scored company profiles
        week_number: Week number of the year (1-52)

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

    # Top 3 highlights (highest confidence)
    highlights = scored_profiles[:3]
    report_lines.append("## Destaques da Semana")
    report_lines.append("")

    for scored in highlights:
        p = scored.profile
        report_lines.append(f"### {p.name}")
        if p.description:
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

    return "\n".join(report_lines)
