"""FUNDING Agent — main agent class orchestrating the funding tracking pipeline.

Inherits from BaseAgent and implements the collect -> process -> score -> output
lifecycle for weekly funding intelligence.
"""

import logging
from datetime import date
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.output import AgentOutput
from apps.agents.funding.collector import FundingEvent, collect_all_sources
from apps.agents.funding.config import FUNDING_CONFIG
from apps.agents.funding.processor import process_events
from apps.agents.funding.scorer import ScoredFundingEvent, score_events
from apps.agents.funding.synthesizer import synthesize_funding_report

logger = logging.getLogger(__name__)


class FundingAgent(BaseAgent):
    """Investment Tracking Agent.

    Monitors VC announcements, funding news sources, and APIs (when available)
    to track funding rounds in LATAM tech companies. Produces weekly funding
    reports with verified amounts and investor information.
    """

    agent_name = "funding"
    version = FUNDING_CONFIG.version

    def __init__(self, week_number: int = 1) -> None:
        """Initialize FUNDING agent.

        Args:
            week_number: Week number of the year (1-52)
        """
        super().__init__()
        self.config = FUNDING_CONFIG
        self.week_number = week_number

    def collect(self) -> list[Any]:
        """Fetch funding events from all configured sources.

        Returns:
            List of raw FundingEvent objects
        """
        sources = self.config.get_enabled_sources()
        logger.info("FUNDING collecting from %d enabled sources", len(sources))

        events = collect_all_sources(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
        )
        return events

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Process and normalize collected funding events.

        Pipeline:
        - Currency normalization (BRL/MXN/ARS → USD)
        - Round type normalization (Série A → series_a)
        - Company name fuzzy matching → slug
        - Deduplication and merging

        Args:
            raw_data: List of raw FundingEvent objects

        Returns:
            List of processed FundingEvent objects
        """
        events: list[FundingEvent] = raw_data

        # TODO: Load known companies from database for fuzzy matching
        # For MVP, we'll generate slugs without database lookup
        known_companies = None

        processed = process_events(events, known_companies=known_companies)

        logger.info(
            "Processed %d funding events (from %d raw)",
            len(processed),
            len(events),
        )

        return processed

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute confidence scores for all funding events.

        Args:
            processed_data: List of processed FundingEvent objects

        Returns:
            List of ConfidenceScore objects (one per event)
        """
        events: list[FundingEvent] = processed_data

        if not events:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        scored: list[ScoredFundingEvent] = score_events(events)

        # Extract just the confidence scores
        scores = [s.confidence for s in scored]

        logger.info(
            "Scored %d funding events. Top confidence: %.2f, Bottom: %.2f",
            len(scores),
            scores[0].composite if scores else 0,
            scores[-1].composite if scores else 0,
        )

        # Store scored events for output phase
        self._scored_events = scored

        return scores

    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Generate the weekly funding report with frontmatter.

        Args:
            processed_data: List of processed FundingEvent objects
            scores: List of ConfidenceScore objects

        Returns:
            AgentOutput with Markdown report
        """
        # Use stored scored events from score() phase
        scored_events: list[ScoredFundingEvent] = getattr(self, "_scored_events", [])

        if not scored_events:
            # Fallback: re-score if needed
            events: list[FundingEvent] = processed_data
            scored_events = score_events(events)

        # Compute aggregate confidence
        if scores:
            avg_dq = sum(s.data_quality for s in scores) / len(scores)
            avg_ac = sum(s.analysis_confidence for s in scores) / len(scores)
            aggregate_confidence = ConfidenceScore(
                data_quality=avg_dq,
                analysis_confidence=avg_ac,
                source_count=len(self.provenance.get_sources()),
                verified=sum(1 for s in scores if s.verified) > len(scores) // 2,
            )
        else:
            aggregate_confidence = ConfidenceScore(
                data_quality=0.3,
                analysis_confidence=0.3,
            )

        # Generate report
        report_md = synthesize_funding_report(
            scored_events=scored_events,
            week_number=self.week_number,
        )

        source_urls = self.provenance.get_source_urls()[:20]

        return AgentOutput(
            title=f"FUNDING Report — Semana {self.week_number}/2026",
            body_md=report_md,
            agent_name=self.agent_name,
            run_id=self.run_id,
            confidence=aggregate_confidence,
            sources=source_urls,
            content_type="DATA_REPORT",
            summary=(
                f"Semana {self.week_number}: {len(scored_events)} rodadas analisadas "
                f"de {len(self.provenance.get_sources())} fontes."
            ),
        )
