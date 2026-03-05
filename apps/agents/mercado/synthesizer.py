"""Content synthesis for MERCADO agent.

Generates Markdown ecosystem reports from scored company profiles.
Uses a section-based approach (mirroring SINTESE) to produce editorial-
quality output grouped by sector, with LLM-generated analysis per section.

When a MercadoWriter is provided, LLM-generated content enriches the report:
  - Ecosystem narrative intro (aggregate trends)
  - Per-sector analysis with contextual company descriptions

Falls back to template-based output when the writer is unavailable or fails.
"""

import logging
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from apps.agents.base.persona_registry import get_display_name
from apps.agents.mercado.scorer import ScoredCompanyProfile

if TYPE_CHECKING:
    from apps.agents.mercado.writer import MercadoWriter

logger = logging.getLogger(__name__)

# Selection parameters
TOP_PROFILES_COUNT = 15
MAX_PER_SECTOR = 5
MAX_PER_CITY = 4


@dataclass
class SectorSection:
    """A section of the report grouped by sector."""

    heading: str
    profiles: list[ScoredCompanyProfile]


def select_top_profiles(
    scored_profiles: list[ScoredCompanyProfile],
    count: int = TOP_PROFILES_COUNT,
    max_per_sector: int = MAX_PER_SECTOR,
    max_per_city: int = MAX_PER_CITY,
) -> list[ScoredCompanyProfile]:
    """Select top profiles ensuring sector and city diversity.

    Profiles are expected to be pre-sorted by composite_score (highest first).
    Caps per-sector and per-city to prevent any one group from dominating.
    """
    selected: list[ScoredCompanyProfile] = []
    sector_counts: dict[str, int] = {}
    city_counts: dict[str, int] = {}

    for scored in scored_profiles:
        sector = scored.profile.sector or "Outros"
        city = scored.profile.city or "N/A"

        if sector_counts.get(sector, 0) >= max_per_sector:
            continue
        if city_counts.get(city, 0) >= max_per_city:
            continue

        selected.append(scored)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        city_counts[city] = city_counts.get(city, 0) + 1

        if len(selected) >= count:
            break

    return selected


def group_by_sector(
    profiles: list[ScoredCompanyProfile],
) -> list[SectorSection]:
    """Group selected profiles into sections by sector.

    Returns sections sorted by profile count (largest first).
    """
    sector_items: dict[str, list[ScoredCompanyProfile]] = {}

    for scored in profiles:
        sector = scored.profile.sector or "Outros"
        if sector not in sector_items:
            sector_items[sector] = []
        sector_items[sector].append(scored)

    # Sort sections by size (largest first)
    sections = sorted(
        sector_items.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )

    return [
        SectorSection(heading=heading, profiles=items)
        for heading, items in sections
    ]


def format_profile_markdown(
    scored: ScoredCompanyProfile,
    index: int,
    description_override: Optional[str] = None,
) -> str:
    """Format a single company profile as Markdown.

    Args:
        scored: The scored profile to format.
        index: The item number in the report.
        description_override: If provided, use instead of original description.
    """
    p = scored.profile
    lines: list[str] = []

    # Linked name: prefer website, fallback to github, then plain
    link_url = p.website or p.github_url
    if link_url:
        lines.append(f"**{index}. [{p.name}]({link_url})**")
    else:
        lines.append(f"**{index}. {p.name}**")

    lines.append(f"*{p.city or 'Local não especificado'}, {p.country} — {p.sector or 'Não classificado'}*")

    # Description: LLM override > original > nothing
    description = description_override
    if description is None and p.description:
        description = p.description.strip()
        if len(description) > 300:
            description = description[:297] + "..."

    if description:
        lines.append(f"> {description}")

    # Metadata bullets
    if p.tech_stack:
        lines.append(f"- **Tech Stack**: {', '.join(p.tech_stack[:5])}")
    if p.github_url and p.website:
        # Only show GitHub separately if we already linked to website
        lines.append(f"- **GitHub**: {p.github_url}")

    lines.append("")
    return "\n".join(lines)


def synthesize_ecosystem_snapshot(
    scored_profiles: list[ScoredCompanyProfile],
    week_number: int,
    writer: Optional["MercadoWriter"] = None,
) -> str:
    """Generate Markdown ecosystem report with sector-based sections.

    When a writer is provided and available, generates LLM-powered editorial
    content (intro paragraph, per-sector analysis with company descriptions).
    Falls back to template-based output when the LLM is unavailable.

    Args:
        scored_profiles: List of scored company profiles (pre-sorted by score).
        week_number: Week number of the year (1-52).
        writer: Optional LLM writer for editorial content enrichment.

    Returns:
        Markdown formatted ecosystem report.
    """
    if not scored_profiles:
        return f"""# Ecossistema LATAM — Semana {week_number}/2026

## Status

Sem novas startups descobertas esta semana.
"""

    total_count = len(scored_profiles)
    top_profiles = select_top_profiles(scored_profiles)
    sections = group_by_sector(top_profiles)

    use_writer = writer is not None and writer.is_available
    persona_name = get_display_name("mercado")

    lines: list[str] = []

    # Header
    lines.append(f"# Ecossistema LATAM — Semana {week_number}/2026")
    lines.append("")
    lines.append(f"*Relatório semanal — Curado por {persona_name} (MERCADO)*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Intro: try LLM, fallback to template
    snapshot_intro = None
    if use_writer:
        try:
            snapshot_intro = writer.write_snapshot_intro(scored_profiles, week_number)
        except Exception:
            logger.warning("Writer failed to generate snapshot intro", exc_info=True)

    if snapshot_intro:
        lines.append(snapshot_intro)
    else:
        unique_cities = len({s.profile.city for s in scored_profiles if s.profile.city})
        unique_sectors = len({s.profile.sector for s in scored_profiles if s.profile.sector})
        lines.append(
            f"Esta semana o MERCADO mapeou **{total_count} startups** em "
            f"**{unique_cities} cidades** e **{unique_sectors} setores** "
            f"no ecossistema tech da América Latina."
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Aggregate context for writer prompts
    aggregate_context = _build_aggregate_context(scored_profiles)

    # Sector sections
    profile_index = 1
    for section in sections:
        section_total = len([
            s for s in scored_profiles
            if (s.profile.sector or "Outros") == section.heading
        ])
        lines.append(f"## {section.heading} ({section_total} startups mapeadas)")
        lines.append("")

        # Try LLM sector analysis
        sector_content = None
        if use_writer:
            try:
                sector_content = writer.write_sector_analysis(section, aggregate_context)
            except Exception:
                logger.warning(
                    "Writer failed for sector %s", section.heading, exc_info=True
                )

        if sector_content:
            lines.append(sector_content.intro)
            lines.append("")
            for i, scored in enumerate(section.profiles):
                desc = (
                    sector_content.descriptions[i]
                    if i < len(sector_content.descriptions)
                    else None
                )
                lines.append(format_profile_markdown(scored, profile_index, description_override=desc))
                profile_index += 1
        else:
            # Template fallback
            for scored in section.profiles:
                lines.append(format_profile_markdown(scored, profile_index))
                profile_index += 1

        lines.append("---")
        lines.append("")

    # Panorama section: aggregate stats
    lines.append("## Panorama do Ecossistema")
    lines.append("")

    # City distribution
    city_counts = Counter(s.profile.city for s in scored_profiles if s.profile.city)
    lines.append("**Distribuição por cidade:**")
    for city, count in city_counts.most_common(8):
        lines.append(f"- {city}: {count} startups")
    lines.append("")

    # Sector distribution
    sector_counts = Counter(s.profile.sector for s in scored_profiles if s.profile.sector)
    lines.append("**Distribuição por setor:**")
    for sector, count in sector_counts.most_common(8):
        lines.append(f"- {sector}: {count} startups")
    lines.append("")

    lines.append(f"*Total: {total_count} startups mapeadas nesta edição.*")
    lines.append("")

    # Editorial mode notice
    if not use_writer:
        lines.append(
            "> *Nota: Este relatorio foi gerado em modo template (sem camada editorial LLM). "
            "As descricoes sao extraidas diretamente das fontes originais. A versao editorial "
            "em portugues requer a configuracao da variavel ANTHROPIC_API_KEY.*"
        )
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        f"Este relatório foi curado por **{persona_name}** na plataforma "
        "[Sinal.lab](https://sinal.tech). O pipeline mapeia startups em "
        "cidades LATAM via GitHub, bases de dados e APIs proprietárias."
    )
    lines.append("")
    lines.append("*Inteligência aberta para quem constrói.*")

    return "\n".join(lines)


def _build_aggregate_context(profiles: list[ScoredCompanyProfile]) -> str:
    """Build aggregate context string for writer prompts."""
    city_counts = Counter(
        s.profile.city or "N/A" for s in profiles
    )
    sector_counts = Counter(
        s.profile.sector or "Outros" for s in profiles
    )

    lines = [
        f"Total: {len(profiles)} startups mapeadas",
        "",
        "Cidades: " + ", ".join(
            f"{city} ({count})" for city, count in city_counts.most_common(5)
        ),
        "Setores: " + ", ".join(
            f"{sector} ({count})" for sector, count in sector_counts.most_common(5)
        ),
    ]
    return "\n".join(lines)
