"""Weekly trend synthesis for RADAR agent.

Takes classified signals and produces a structured trend report,
highlighting the top emerging signals grouped by category with
momentum indicators.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from apps.agents.base.llm import strip_html
from apps.agents.radar.classifier import ClassifiedSignal

if TYPE_CHECKING:
    from apps.agents.radar.writer import RadarWriter

logger = logging.getLogger(__name__)

TOP_SIGNALS_COUNT = 15
MIN_SCORE_THRESHOLD = 0.10

# Display names for topic categories
TOPIC_DISPLAY_NAMES: dict[str, str] = {
    "ai_ml": "IA & Machine Learning",
    "infrastructure": "Infraestrutura Cloud & DevOps",
    "developer_tools": "Ferramentas de Desenvolvimento & Open Source",
    "startup_ecosystem": "Startups & Ecossistema",
    "fintech": "Fintech & Pagamentos",
    "latam_tech": "Ecossistema LATAM",
    "security": "Seguranca & Privacidade",
    "data_engineering": "Engenharia de Dados & Analytics",
    "uncategorized": "Outros Sinais",
}


@dataclass
class TrendSection:
    """A section of the trend report with a heading and signals."""

    heading: str
    topic_key: str
    signals: list[ClassifiedSignal]


def momentum_indicator(score: float) -> str:
    """Return a text momentum indicator based on score."""
    if score >= 0.8:
        return "[FORTE]"
    elif score >= 0.5:
        return "[MEDIO]"
    elif score >= 0.3:
        return "[LEVE]"
    else:
        return "[FRACO]"


def select_top_signals(
    classified: list[ClassifiedSignal],
    count: int = TOP_SIGNALS_COUNT,
    min_score: float = MIN_SCORE_THRESHOLD,
) -> list[ClassifiedSignal]:
    """Select top signals with source diversity.

    Limits to max 4 items per source to prevent domination.
    """
    selected: list[ClassifiedSignal] = []
    source_counts: dict[str, int] = {}
    max_per_source = 4

    for item in classified:
        if item.composite_score < min_score:
            continue

        source = item.signal.source_name
        current = source_counts.get(source, 0)
        if current >= max_per_source:
            continue

        selected.append(item)
        source_counts[source] = current + 1

        if len(selected) >= count:
            break

    return selected


def group_by_topic(signals: list[ClassifiedSignal]) -> list[TrendSection]:
    """Group signals into sections by primary topic."""
    topic_items: dict[str, list[ClassifiedSignal]] = {}

    for signal in signals:
        key = signal.primary_topic
        if key not in topic_items:
            topic_items[key] = []
        topic_items[key].append(signal)

    # Sort sections: largest first, uncategorized last
    sections: list[TrendSection] = []
    uncategorized = topic_items.pop("uncategorized", None)

    sorted_topics = sorted(
        topic_items.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )

    for topic_key, items in sorted_topics:
        heading = TOPIC_DISPLAY_NAMES.get(topic_key, topic_key.replace("_", " ").title())
        sections.append(TrendSection(heading=heading, topic_key=topic_key, signals=items))

    if uncategorized:
        sections.append(TrendSection(
            heading="Outros Sinais",
            topic_key="uncategorized",
            signals=uncategorized,
        ))

    return sections


def format_signal_markdown(signal: ClassifiedSignal, index: int) -> str:
    """Format a single trend signal as Markdown."""
    lines: list[str] = []
    mi = momentum_indicator(signal.momentum_score)

    lines.append(f"**{index}. [{signal.signal.title}]({signal.signal.url})** {mi}")
    lines.append(f"*Fonte: {signal.signal.source_name} | Topicos: {', '.join(signal.topics[:3])}*")

    if signal.signal.summary:
        summary = strip_html(signal.signal.summary)
        lines.append(f"> {summary}")

    # Show key metrics if available
    metrics = signal.signal.metrics
    if metrics.get("stars"):
        lines.append(f"  Estrelas: {metrics['stars']:,} | Linguagem: {metrics.get('language', 'N/A')}")

    lines.append("")
    return "\n".join(lines)


def format_signal_markdown_with_summary(
    signal: ClassifiedSignal,
    index: int,
    summary_override: Optional[str] = None,
) -> str:
    """Format a single trend signal as Markdown, optionally with an LLM summary.

    Args:
        signal: The classified signal to format.
        index: The signal number in the report.
        summary_override: If provided, use this instead of the original summary.
    """
    lines: list[str] = []
    mi = momentum_indicator(signal.momentum_score)

    lines.append(f"**{index}. [{signal.signal.title}]({signal.signal.url})** {mi}")
    lines.append(f"*Fonte: {signal.signal.source_name} | Topicos: {', '.join(signal.topics[:3])}*")

    summary = summary_override
    if summary is None and signal.signal.summary:
        summary = strip_html(signal.signal.summary)

    if summary:
        lines.append(f"> {summary}")

    # Show key metrics if available
    metrics = signal.signal.metrics
    if metrics.get("stars"):
        lines.append(f"  Estrelas: {metrics['stars']:,} | Linguagem: {metrics.get('language', 'N/A')}")

    lines.append("")
    return "\n".join(lines)


def synthesize_trend_report(
    classified: list[ClassifiedSignal],
    week_number: int = 1,
    report_date: Optional[datetime] = None,
    writer: Optional["RadarWriter"] = None,
) -> str:
    """Produce the full trend report in Markdown.

    When a writer is provided and available, generates LLM-powered editorial
    content (intro paragraph, section analysis, rewritten summaries).
    Falls back to template-based output per-piece when the LLM is unavailable
    or returns None.

    Args:
        classified: All classified signals (will be filtered and ranked).
        week_number: Week number for the report title.
        report_date: Date for the report (defaults to now).
        writer: Optional LLM editorial writer for enhanced content.

    Returns:
        Complete trend report Markdown ready for review and publication.
    """
    if not report_date:
        report_date = datetime.now(timezone.utc)

    date_str = report_date.strftime("%d/%m/%Y")

    top_signals = select_top_signals(classified)
    sections = group_by_topic(top_signals)

    use_writer = writer is not None and writer.is_available

    lines: list[str] = []

    # Header
    lines.append(f"# RADAR Semanal — Semana {week_number}")
    lines.append("")
    lines.append(f"*{date_str} — Detectado pelo agente RADAR*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Intro: try LLM, fallback to template
    llm_intro = None
    if use_writer:
        llm_intro = writer.write_report_intro(sections, week_number)

    if llm_intro:
        lines.append(llm_intro)
    else:
        # Template fallback: summary stats
        topic_counts: dict[str, int] = {}
        for s in top_signals:
            topic_counts[s.primary_topic] = topic_counts.get(s.primary_topic, 0) + 1

        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_topic_names = [
            TOPIC_DISPLAY_NAMES.get(t[0], t[0]) for t in top_topics
        ]

        lines.append(
            f"**{len(top_signals)} sinais emergentes** detectados esta semana "
            f"de **{len(set(s.signal.source_name for s in top_signals))} fontes**. "
            f"Areas mais ativas: {', '.join(top_topic_names) if top_topic_names else 'diversas'}."
        )
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
            # LLM editorial analysis
            lines.append(section_content.intro)
            lines.append("")
            for i, classified_signal in enumerate(section.signals):
                lines.append(format_signal_markdown_with_summary(
                    classified_signal, signal_index,
                    summary_override=section_content.summaries[i],
                ))
                signal_index += 1
        else:
            # Template fallback
            for classified_signal in section.signals:
                lines.append(format_signal_markdown(classified_signal, signal_index))
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
        "O agente **RADAR** monitora Hacker News, GitHub trending, arXiv, "
        "Google Trends e comunidades tech para identificar sinais emergentes. "
        "Cada sinal e classificado por topico, pontuado por momentum "
        "(recencia + engajamento) e relevancia para a America Latina."
    )
    lines.append("")
    lines.append("*Sinal.lab — Inteligencia aberta para quem constroi.*")

    return "\n".join(lines)
