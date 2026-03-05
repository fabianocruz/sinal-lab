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
from apps.agents.sintese.collector import FeedItem, collect_all_sources
from apps.agents.sintese.config import SINTESE_CONFIG
from apps.agents.sintese.scorer import ScoredItem, score_items
from apps.agents.sintese.synthesizer import synthesize_newsletter
from apps.agents.sintese.writer import SinteseWriter

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
        """Fetch all configured sources (RSS + Twitter)."""
        sources = self.config.get_enabled_sources()
        logger.info("Collecting from %d enabled sources", len(sources))

        items = collect_all_sources(
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
        """Generate the newsletter Markdown with frontmatter and rich metadata."""
        scored_items: list[ScoredItem] = processed_data
        confidence = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3
        )

        writer = SinteseWriter()
        newsletter_md, sections = synthesize_newsletter(
            scored_items=scored_items,
            edition_number=self.edition_number,
            writer=writer,
        )

        source_urls = self.provenance.get_source_urls()[:20]

        # Select hero image from highest-scored item that has an image
        hero_image = None
        for s in scored_items[:15]:
            if getattr(s.item, "image_url", None):
                hero_image = {
                    "url": s.item.image_url,
                    "alt": s.item.title,
                    "caption": f"Fonte: {s.item.source_name}",
                }
                break

        # Build section labels from synthesizer categories
        section_labels = {
            f"section_{i + 1}": section.heading
            for i, section in enumerate(sections)
        }

        # LLM-generated editorial metadata (Phase 3)
        editorial_meta = None
        if writer.is_available:
            editorial_meta = writer.write_editorial_metadata(sections, self.edition_number)

        # Extract structured per-item data for email rendering and API
        metadata = {
            "hero_image": hero_image,
            "featured_video": (
                {"url": editorial_meta.featured_video_url, "title": None, "caption": None}
                if editorial_meta and editorial_meta.featured_video_url
                else None
            ),
            "callouts": editorial_meta.callouts if editorial_meta else [],
            "section_labels": section_labels,
            "reading_time_minutes": max(1, len(newsletter_md.split()) // 200),
            "edition_number": self.edition_number,
            "companies_mentioned": editorial_meta.companies_mentioned if editorial_meta else [],
            "topics": editorial_meta.topics if editorial_meta else [],
            "items": [
                {
                    "title": s.item.title,
                    "url": s.item.url,
                    "source_name": s.item.source_name,
                    "summary": (s.item.summary or "")[:200],
                    "composite_score": round(s.composite_score, 3),
                    "image_url": getattr(s.item, "image_url", None),
                    "video_url": getattr(s.item, "video_url", None),
                }
                for s in scored_items[:15]
            ],
            "item_count": len(scored_items),
            "total_sources": len(self.provenance.get_sources()),
        }

        # Generate editorial title via LLM (falls back to branded template)
        editorial_title = writer.write_headline(sections, self.edition_number)
        if not editorial_title:
            editorial_title = f"Sinal Semanal #{self.edition_number}"

        return AgentOutput(
            title=editorial_title,
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
            metadata=metadata,
        )
