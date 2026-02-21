"""RADAR Agent — main agent class orchestrating the trend detection pipeline.

Inherits from BaseAgent and implements the collect -> process -> score -> output
lifecycle for weekly trend intelligence.
"""

import logging
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.radar.classifier import ClassifiedSignal, classify_signals
from apps.agents.radar.collector import TrendSignal, collect_all_sources
from apps.agents.radar.config import RADAR_CONFIG
from apps.agents.radar.synthesizer import synthesize_trend_report
from apps.agents.radar.writer import RadarWriter

logger = logging.getLogger(__name__)


class RadarAgent(BaseAgent):
    """Trend Intelligence Agent.

    Monitors HN, GitHub trending, arXiv, Google Trends, and tech
    communities to detect emerging signals relevant to the LATAM
    tech ecosystem.
    """

    agent_name = "radar"
    agent_category = AgentCategory.CONTENT.value
    version = RADAR_CONFIG.version

    def __init__(self, week_number: int = 1) -> None:
        super().__init__()
        self.config = RADAR_CONFIG
        self.week_number = week_number

    def collect(self) -> list[Any]:
        """Fetch signals from all configured sources."""
        sources = self.config.get_enabled_sources()
        logger.info("RADAR collecting from %d enabled sources", len(sources))

        signals = collect_all_sources(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
        )
        return signals

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Classify and score all collected signals."""
        signals: list[TrendSignal] = raw_data
        classified = classify_signals(signals)
        logger.info(
            "Classified %d signals. Top composite: %.3f",
            len(classified),
            classified[0].composite_score if classified else 0,
        )
        return classified

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute overall confidence for this trend report."""
        classified: list[ClassifiedSignal] = processed_data

        if not classified:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        source_names = set(s.signal.source_name for s in classified[:30])
        source_count = len(source_names)

        confidence = compute_confidence(
            source_count=source_count,
            sources_verified=0,
            data_freshness_days=0,
        )
        return [confidence]

    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Generate the trend report with frontmatter."""
        classified: list[ClassifiedSignal] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3
        )

        writer = RadarWriter()
        report_md = synthesize_trend_report(
            classified=classified,
            week_number=self.week_number,
            writer=writer,
        )

        source_urls = self.provenance.get_source_urls()[:20]

        # Extract structured per-item data for email rendering and API
        metadata = {
            "items": [
                {
                    "title": s.signal.title,
                    "url": s.signal.url,
                    "source_name": s.signal.source_name,
                    "source_type": s.signal.source_type,
                    "summary": (s.signal.summary or "")[:200],
                    "metrics": s.signal.metrics,
                    "momentum_score": round(s.momentum_score, 3),
                    "primary_topic": s.primary_topic,
                }
                for s in classified[:10]
            ],
            "item_count": len(classified),
            "total_sources": len(self.provenance.get_sources()),
        }

        return AgentOutput(
            title=f"RADAR Semanal — Semana {self.week_number}",
            body_md=report_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=source_urls,
            content_type="ANALYSIS",
            summary=(
                f"Semana {self.week_number}: {len(classified)} sinais analisados "
                f"de {len(self.provenance.get_sources())} fontes."
            ),
            metadata=metadata,
        )
