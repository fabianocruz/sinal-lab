"""Weekly dev ecosystem report synthesizer for CODIGO agent.

Takes analyzed signals and produces a structured report highlighting
top frameworks, rising libraries, notable repos, and language trends.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from apps.agents.codigo.analyzer import AnalyzedSignal

logger = logging.getLogger(__name__)

TOP_SIGNALS_COUNT = 15
MIN_SCORE_THRESHOLD = 0.10

CATEGORY_DISPLAY: dict[str, str] = {
    "ai_frameworks": "AI Frameworks & Tools",
    "web_frameworks": "Web Frameworks",
    "developer_tools": "Developer Tools",
    "infrastructure": "Infraestrutura & DevOps",
    "databases": "Databases & Data Tools",
    "security": "Seguranca",
    "general": "Outros Destaques",
}

ADOPTION_DISPLAY: dict[str, str] = {
    "rising": "[SUBINDO]",
    "stable": "[ESTAVEL]",
    "declining": "[QUEDA]",
    "new": "[NOVO]",
}


@dataclass
class ReportSection:
    """A section of the dev ecosystem report."""

    heading: str
    category_key: str
    signals: list[AnalyzedSignal]


def select_top_signals(
    analyzed: list[AnalyzedSignal],
    count: int = TOP_SIGNALS_COUNT,
    min_score: float = MIN_SCORE_THRESHOLD,
) -> list[AnalyzedSignal]:
    """Select top signals with source diversity (max 4 per source)."""
    selected: list[AnalyzedSignal] = []
    source_counts: dict[str, int] = {}

    for item in analyzed:
        if item.composite_score < min_score:
            continue

        source = item.signal.source_name
        if source_counts.get(source, 0) >= 4:
            continue

        selected.append(item)
        source_counts[source] = source_counts.get(source, 0) + 1

        if len(selected) >= count:
            break

    return selected


def group_by_category(signals: list[AnalyzedSignal]) -> list[ReportSection]:
    """Group signals by dev category."""
    cat_items: dict[str, list[AnalyzedSignal]] = {}

    for signal in signals:
        key = signal.category
        if key not in cat_items:
            cat_items[key] = []
        cat_items[key].append(signal)

    general = cat_items.pop("general", None)
    sections: list[ReportSection] = []

    sorted_cats = sorted(cat_items.items(), key=lambda x: len(x[1]), reverse=True)
    for key, items in sorted_cats:
        heading = CATEGORY_DISPLAY.get(key, key.replace("_", " ").title())
        sections.append(ReportSection(heading=heading, category_key=key, signals=items))

    if general:
        sections.append(ReportSection(
            heading="Outros Destaques",
            category_key="general",
            signals=general,
        ))

    return sections


def format_signal_markdown(signal: AnalyzedSignal, index: int) -> str:
    """Format a single dev signal as Markdown."""
    lines: list[str] = []
    adoption = ADOPTION_DISPLAY.get(signal.adoption_indicator, "")

    lines.append(f"**{index}. [{signal.signal.title}]({signal.signal.url})** {adoption}")

    meta_parts = [f"Fonte: {signal.signal.source_name}"]
    if signal.signal.language:
        meta_parts.append(f"Lang: {signal.signal.language}")
    lines.append(f"*{' | '.join(meta_parts)}*")

    if signal.signal.summary:
        import re
        summary = re.sub(r"<[^>]+>", "", signal.signal.summary.strip())
        if len(summary) > 300:
            summary = summary[:297] + "..."
        lines.append(f"> {summary}")

    metrics = signal.signal.metrics
    metric_parts = []
    if metrics.get("stars"):
        metric_parts.append(f"Stars: {metrics['stars']:,}")
    if metrics.get("forks"):
        metric_parts.append(f"Forks: {metrics['forks']:,}")
    if metric_parts:
        lines.append(f"  {' | '.join(metric_parts)}")

    lines.append("")
    return "\n".join(lines)


def synthesize_dev_report(
    analyzed: list[AnalyzedSignal],
    week_number: int = 1,
    report_date: Optional[datetime] = None,
) -> str:
    """Produce the full dev ecosystem report in Markdown."""
    if not report_date:
        report_date = datetime.now(timezone.utc)

    date_str = report_date.strftime("%d/%m/%Y")
    top_signals = select_top_signals(analyzed)
    sections = group_by_category(top_signals)

    lines: list[str] = []

    # Header
    lines.append(f"# CODIGO Semanal — Semana {week_number}")
    lines.append("")
    lines.append(f"*{date_str} — Monitorado pelo agente CODIGO*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Language summary
    lang_counts: dict[str, int] = {}
    for s in top_signals:
        lang = s.signal.language or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    lang_summary = ", ".join(f"{l[0]} ({l[1]})" for l in top_langs if l[0] != "unknown")

    lines.append(
        f"**{len(top_signals)} sinais dev** analisados esta semana de "
        f"**{len(set(s.signal.source_name for s in top_signals))} fontes**."
    )
    if lang_summary:
        lines.append(f"Linguagens em destaque: {lang_summary}.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    signal_index = 1
    for section in sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        for analyzed_signal in section.signals:
            lines.append(format_signal_markdown(analyzed_signal, signal_index))
            signal_index += 1
        lines.append("---")
        lines.append("")

    # Footer
    lines.append("## Metodologia")
    lines.append("")
    lines.append(
        "O agente **CODIGO** monitora GitHub trending (daily/weekly), registro npm, "
        "PyPI, Stack Overflow, e comunidades dev para identificar frameworks, "
        "bibliotecas e ferramentas em ascensao. Cada sinal e analisado por "
        "momentum, atividade da comunidade e relevancia da linguagem."
    )
    lines.append("")
    lines.append("*Sinal.lab — Inteligencia aberta para quem constroi.*")

    return "\n".join(lines)
