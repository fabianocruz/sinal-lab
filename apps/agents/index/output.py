"""Output formatting for INDEX agent.

Generates a Markdown report summarizing the INDEX pipeline run:
companies discovered, sources used, dedup statistics.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput, format_markdown_output
from apps.agents.index.pipeline import MergedCompany

logger = logging.getLogger(__name__)


def generate_index_report(
    scored_companies: list[tuple[MergedCompany, float]],
    run_id: str,
    sources_used: list[str],
    persist_stats: dict[str, int] | None = None,
) -> AgentOutput:
    """Generate Markdown report for INDEX pipeline run.

    Args:
        scored_companies: List of (MergedCompany, score) tuples.
        run_id: Agent run ID.
        sources_used: List of source names used.
        persist_stats: Optional persistence stats.

    Returns:
        AgentOutput with formatted report.
    """
    total = len(scored_companies)
    new_count = sum(1 for m, _ in scored_companies if m.is_new)
    update_count = total - new_count

    # Count by source
    source_counts: dict[str, int] = {}
    for merged, _ in scored_companies:
        for source in merged.sources:
            source_counts[source] = source_counts.get(source, 0) + 1

    # Count by country
    country_counts: dict[str, int] = {}
    for merged, _ in scored_companies:
        country = merged.country or "Unknown"
        country_counts[country] = country_counts.get(country, 0) + 1

    # Top companies
    top_10 = scored_companies[:10]

    # Build sections
    sections = []

    # Summary section
    summary_lines = [
        f"**{total}** empresas processadas ({new_count} novas, {update_count} atualizadas)",
        f"**{len(sources_used)}** fontes de dados utilizadas",
    ]
    if persist_stats:
        summary_lines.append(
            f"**Persistência:** {persist_stats.get('inserted', 0)} inseridas, "
            f"{persist_stats.get('updated', 0)} atualizadas, "
            f"{persist_stats.get('skipped', 0)} ignoradas"
        )
    sections.append({"heading": "Resumo", "content": "\n".join(summary_lines)})

    # Source breakdown
    source_lines = []
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        source_lines.append(f"- **{source}**: {count} empresas")
    sections.append({"heading": "Fontes de Dados", "content": "\n".join(source_lines)})

    # Country breakdown
    country_lines = []
    for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        country_lines.append(f"- **{country}**: {count} empresas")
    sections.append({"heading": "Distribuição por País", "content": "\n".join(country_lines)})

    # Top companies table
    if top_10:
        table_lines = ["| # | Empresa | Score | Fontes | Cidade |", "|---|---------|-------|--------|--------|"]
        for i, (merged, score) in enumerate(top_10, 1):
            sources_str = ", ".join(merged.sources[:3])
            table_lines.append(
                f"| {i} | {merged.name} | {score:.3f} | {sources_str} | {merged.city or '-'} |"
            )
        sections.append({"heading": "Top 10 Empresas", "content": "\n".join(table_lines)})

    # Compute aggregate confidence
    if scored_companies:
        avg_score = sum(s for _, s in scored_companies) / total
        max_score = max(s for _, s in scored_companies)
        multi_source = sum(1 for m, _ in scored_companies if m.source_count >= 2)
        multi_source_ratio = multi_source / total

        confidence = ConfidenceScore(
            data_quality=round(min(avg_score * 1.2, 0.95), 3),
            analysis_confidence=round(avg_score, 3),
            source_count=len(sources_used),
            verified=multi_source_ratio > 0.3,
        )
    else:
        confidence = ConfidenceScore(data_quality=0.3, analysis_confidence=0.3)

    return format_markdown_output(
        title=f"INDEX Report — {total} LATAM Startups",
        sections=sections,
        agent_name="index",
        run_id=run_id,
        confidence=confidence,
        sources=sources_used,
        content_type="DATA_REPORT",
        agent_category="data",
        summary=f"{total} startups processadas de {len(sources_used)} fontes ({new_count} novas).",
    )
