"""Weekly dev ecosystem report synthesizer for CODIGO agent.

Takes analyzed signals and produces a structured report highlighting
top frameworks, rising libraries, notable repos, and language trends.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from apps.agents.base.llm import strip_html
from apps.agents.base.persona_registry import get_display_name
from apps.agents.codigo.analyzer import AnalyzedSignal

if TYPE_CHECKING:
    from apps.agents.codigo.writer import CodigoWriter

logger = logging.getLogger(__name__)

TOP_SIGNALS_COUNT = 15
MIN_SCORE_THRESHOLD = 0.10

CATEGORY_DISPLAY: dict[str, str] = {
    "ai_frameworks": "Frameworks & Ferramentas de IA",
    "web_frameworks": "Frameworks Web",
    "developer_tools": "Ferramentas de Desenvolvimento",
    "infrastructure": "Infraestrutura & DevOps",
    "databases": "Bancos de Dados & Data Tools",
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


def format_signal_markdown(
    signal: AnalyzedSignal,
    index: int,
    summary_override: Optional[str] = None,
) -> str:
    """Format a single dev signal as Markdown.

    Args:
        signal: The analyzed signal to format.
        index: The signal number in the report.
        summary_override: If provided, use this instead of the original summary.
    """
    lines: list[str] = []
    adoption = ADOPTION_DISPLAY.get(signal.adoption_indicator, "")

    lines.append(f"**{index}. [{signal.signal.title}]({signal.signal.url})** {adoption}")

    meta_parts = [f"Fonte: {signal.signal.source_name}"]
    if signal.signal.language:
        meta_parts.append(f"Linguagem: {signal.signal.language}")
    lines.append(f"*{' | '.join(meta_parts)}*")

    summary = summary_override
    if summary is None and signal.signal.summary:
        summary = strip_html(signal.signal.summary)

    if summary:
        lines.append(f"> {summary}")

    metrics = signal.signal.metrics
    metric_parts = []
    if metrics.get("stars"):
        metric_parts.append(f"Estrelas: {metrics['stars']:,}")
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
    writer: Optional["CodigoWriter"] = None,
) -> str:
    """Produce the full dev ecosystem report in Markdown.

    When a writer is provided and available, generates LLM-powered editorial
    content (intro paragraph, section commentary, rewritten summaries).
    Falls back to template-based output per-piece when the LLM is unavailable
    or returns None.

    Args:
        analyzed: All analyzed signals (will be filtered and ranked).
        week_number: Sequential report week number.
        report_date: Date for the report (defaults to now).
        writer: Optional LLM editorial writer for enhanced content.

    Returns:
        Complete report Markdown ready for review and publication.
    """
    if not report_date:
        report_date = datetime.now(timezone.utc)

    date_str = report_date.strftime("%d/%m/%Y")
    top_signals = select_top_signals(analyzed)
    sections = group_by_category(top_signals)

    use_writer = writer is not None and writer.is_available

    lines: list[str] = []

    # Header
    lines.append(f"# CODIGO Semanal — Semana {week_number}")
    lines.append("")
    persona_name = get_display_name("codigo")
    lines.append(f"*{date_str} — Monitorado por {persona_name} (CODIGO)*")
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

    # Intro: try LLM, fallback to template
    llm_intro = None
    if use_writer:
        llm_intro = writer.write_report_intro(sections, week_number)

    if llm_intro:
        lines.append(llm_intro)
    else:
        lines.append(
            f"**{len(top_signals)} sinais dev** analisados esta semana de "
            f"**{len(set(s.signal.source_name for s in top_signals))} fontes**."
        )
        if lang_summary:
            lines.append(f"Linguagens em destaque: {lang_summary}.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections: try LLM per section, fallback to template
    signal_index = 1
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
            for i, analyzed_signal in enumerate(section.signals):
                lines.append(format_signal_markdown(
                    analyzed_signal, signal_index,
                    summary_override=section_content.summaries[i],
                ))
                signal_index += 1
        else:
            # Template fallback
            for analyzed_signal in section.signals:
                lines.append(format_signal_markdown(analyzed_signal, signal_index))
                signal_index += 1

        lines.append("---")
        lines.append("")

    # Editorial mode notice
    if not use_writer:
        lines.append(
            "> *Nota: Este relatorio foi gerado em modo template (sem camada editorial LLM). "
            "Os resumos abaixo sao extraidos diretamente das fontes originais e podem conter "
            "conteudo em ingles ou outros idiomas. A versao editorial em portugues requer "
            "a configuracao da variavel ANTHROPIC_API_KEY.*"
        )
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
