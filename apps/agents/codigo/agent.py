"""CODIGO Agent — main agent class orchestrating the dev ecosystem pipeline.

Inherits from BaseAgent and implements collect -> process -> score -> output
for weekly developer ecosystem intelligence.
"""

import logging
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.codigo.analyzer import AnalyzedSignal, analyze_signals
from apps.agents.codigo.collector import DevSignal, collect_all_sources
from apps.agents.codigo.config import CODIGO_CONFIG
from apps.agents.codigo.synthesizer import synthesize_dev_report

logger = logging.getLogger(__name__)


class CodigoAgent(BaseAgent):
    """Developer Ecosystem Signals Agent.

    Monitors GitHub trending, npm, PyPI, Stack Overflow, and dev
    communities to track framework adoption, library momentum,
    and technology trends.
    """

    agent_name = "codigo"
    agent_category = AgentCategory.CONTENT.value
    version = CODIGO_CONFIG.version

    def __init__(self, week_number: int = 1) -> None:
        super().__init__()
        self.config = CODIGO_CONFIG
        self.week_number = week_number

    def collect(self) -> list[Any]:
        """Fetch signals from all configured dev ecosystem sources."""
        sources = self.config.get_enabled_sources()
        logger.info("CODIGO collecting from %d enabled sources", len(sources))

        signals = collect_all_sources(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
        )
        return signals

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Analyze and score all collected dev signals."""
        signals: list[DevSignal] = raw_data
        analyzed = analyze_signals(signals)
        logger.info(
            "Analyzed %d signals. Top composite: %.3f",
            len(analyzed),
            analyzed[0].composite_score if analyzed else 0,
        )
        return analyzed

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute overall confidence for this dev report."""
        analyzed: list[AnalyzedSignal] = processed_data

        if not analyzed:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        source_names = set(s.signal.source_name for s in analyzed[:30])
        confidence = compute_confidence(
            source_count=len(source_names),
            sources_verified=0,
            data_freshness_days=0,
        )
        return [confidence]

    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Generate the dev ecosystem report with frontmatter."""
        analyzed: list[AnalyzedSignal] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3
        )

        report_md = synthesize_dev_report(
            analyzed=analyzed,
            week_number=self.week_number,
        )

        source_urls = self.provenance.get_source_urls()[:20]

        return AgentOutput(
            title=f"CODIGO Semanal — Semana {self.week_number}",
            body_md=report_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=source_urls,
            content_type="ANALYSIS",
            summary=(
                f"Semana {self.week_number}: {len(analyzed)} sinais dev analisados "
                f"de {len(self.provenance.get_sources())} fontes."
            ),
        )
