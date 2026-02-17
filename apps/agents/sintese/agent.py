"""SINTESE Agent — main agent class orchestrating the newsletter pipeline.

Inherits from BaseAgent and implements the collect -> process -> score -> output
lifecycle for newsletter production.
"""

import logging
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore, compute_confidence
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.sintese.collector import FeedItem, collect_all_feeds
from apps.agents.sintese.config import SINTESE_CONFIG
from apps.agents.sintese.scorer import ScoredItem, score_items
from apps.agents.sintese.synthesizer import synthesize_newsletter

logger = logging.getLogger(__name__)


class SinteseAgent(BaseAgent):
    """Newsletter Synthesizer Agent.

    Aggregates 100+ RSS feeds of LATAM tech news, scores items by
    relevance, and produces a curated weekly newsletter draft.
    """

    agent_name = "sintese"
    agent_category = AgentCategory.CONTENT.value
    version = SINTESE_CONFIG.version

    def __init__(self, edition_number: int = 1) -> None:
        super().__init__()
        self.config = SINTESE_CONFIG
        self.edition_number = edition_number

    def collect(self) -> list[Any]:
        """Fetch all configured RSS/Atom feeds."""
        sources = self.config.get_enabled_sources()
        logger.info("Collecting from %d enabled sources", len(sources))

        items = collect_all_feeds(
            sources=sources,
            provenance=self.provenance,
            agent_name=self.agent_name,
            run_id=self.run_id,
        )
        return items

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Score and rank collected items by relevance."""
        items: list[FeedItem] = raw_data
        scored = score_items(items)
        logger.info(
            "Scored %d items. Top score: %.3f, Bottom score: %.3f",
            len(scored),
            scored[0].composite_score if scored else 0,
            scored[-1].composite_score if scored else 0,
        )
        return scored

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute overall confidence for this newsletter edition."""
        scored_items: list[ScoredItem] = processed_data

        if not scored_items:
            return [ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)]

        # Aggregate confidence from individual item scores
        source_names = set(item.item.source_name for item in scored_items[:20])
        source_count = len(source_names)

        confidence = compute_confidence(
            source_count=source_count,
            sources_verified=0,  # RSS feeds are not independently verified
            data_freshness_days=0,  # We collect fresh data each run
        )

        return [confidence]

    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Generate the newsletter Markdown with frontmatter."""
        scored_items: list[ScoredItem] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3
        )

        newsletter_md = synthesize_newsletter(
            scored_items=scored_items,
            edition_number=self.edition_number,
        )

        source_urls = self.provenance.get_source_urls()[:20]

        return AgentOutput(
            title=f"Sinal Semanal #{self.edition_number}",
            body_md=newsletter_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=source_urls,
            content_type="DATA_REPORT",
            summary=(
                f"Edicao #{self.edition_number} do Sinal Semanal — "
                f"{len(scored_items)} itens analisados de {len(self.provenance.get_sources())} fontes."
            ),
        )
