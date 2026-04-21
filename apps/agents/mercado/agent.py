"""MERCADO v2 Agent — Market Intelligence Weekly for LATAM tech.

v2 is a READER, not a scraper. It queries:
- funding_rounds (populated by FUNDING agent)
- companies (populated by INDEX agent)

And produces a weekly editorial analysis of market movements, organized
by sector, following the same editorial bar as SINTESE/RADAR.

Scraping responsibility moved to INDEX agent.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.mercado.market_event import MarketEvent, ScoredEvent, SectorSection
from apps.agents.mercado.v2_classifier import build_sections
from apps.agents.mercado.v2_collector import (
    collect_funding_events,
    enrich_events_with_companies,
)
from apps.agents.mercado.v2_scorer import score_and_rank_sections
from apps.agents.mercado.v2_synthesizer import synthesize_market_intel
from apps.agents.mercado.v2_writer import EditorialMetadata, MercadoV2Writer

logger = logging.getLogger(__name__)


class MercadoAgent(BaseAgent):
    """MERCADO v2 — Market Intelligence Weekly."""

    agent_name = "mercado"
    agent_category = AgentCategory.CONTENT.value  # v2 produces editorial, not data

    def __init__(self, week_number: int) -> None:
        super().__init__()
        self.week_number = week_number
        self.provenance = ProvenanceTracker()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_id = f"mercado-{timestamp}"
        self._sections: list[SectorSection] = []
        logger.info("Initialized MERCADO v2 agent: week=%d, run_id=%s", week_number, self.run_id)

    def collect(self) -> list[Any]:
        """Collect market events from the database."""
        logger.info("Starting COLLECT phase (v2: reader mode)")

        from packages.database.session import get_session
        session = get_session()
        try:
            # 7-day window is primary (what we report on)
            events = collect_funding_events(session, days_back=7)
            events = enrich_events_with_companies(session, events)

            # If 7d is too thin, widen to 14d to bootstrap the edition.
            if len(events) < 5:
                logger.info("Thin week (%d events in 7d), widening to 14d", len(events))
                events = collect_funding_events(session, days_back=14)
                events = enrich_events_with_companies(session, events)

            self.provenance.track(
                source_url=None,
                source_name="funding_rounds_db",
                extraction_method="database",
            )
            logger.info("COLLECT complete: %d market events", len(events))
            return events  # type: ignore[return-value]
        finally:
            session.close()

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Group events into editorial sections by sector."""
        events: list[MarketEvent] = raw_data
        logger.info("Starting PROCESS phase: %d events", len(events))

        sections = build_sections(events, max_sections=4, min_events_per_section=2)
        logger.info(
            "PROCESS complete: %d sections (%s)",
            len(sections),
            ", ".join(s.sector_slug for s in sections),
        )
        self._sections = sections
        return sections  # type: ignore[return-value]

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Score events within each section and keep top-N per section."""
        sections: list[SectorSection] = processed_data
        logger.info("Starting SCORE phase")

        scored_sections = score_and_rank_sections(sections, max_events_per_section=5)
        self._sections = scored_sections

        # Aggregate confidence: sources used, average editorial score
        total_events = sum(len(s.events) for s in scored_sections)
        if total_events == 0:
            return [ConfidenceScore(data_quality=0.3, analysis_confidence=0.3)]

        all_scored: list[ScoredEvent] = [
            e for s in scored_sections for e in s.events  # type: ignore[misc]
        ]
        avg_score = (
            sum(e.editorial_score for e in all_scored) / len(all_scored)
            if all_scored else 0.5
        )
        return [ConfidenceScore(
            data_quality=min(0.95, avg_score + 0.1),
            analysis_confidence=avg_score,
            source_count=1,  # single DB source
            verified=all_scored and all_scored[0].editorial_score >= 0.7,
        )]

    def output(self, processed_data: list[Any], scores: list[Any]) -> AgentOutput:
        """Generate newsletter Markdown + rich metadata."""
        sections: list[SectorSection] = self._sections
        confidence: ConfidenceScore = scores[0] if scores else ConfidenceScore(
            data_quality=0.3, analysis_confidence=0.3
        )
        logger.info("Starting OUTPUT phase: %d sections", len(sections))

        writer = MercadoV2Writer()
        body_md, editorial_meta = synthesize_market_intel(
            sections=sections,
            week_number=self.week_number,
            writer=writer,
        )

        # Headline via LLM
        title: Optional[str] = None
        if writer.is_available and sections:
            try:
                title = writer.write_headline(sections, self.week_number)
            except Exception:
                logger.warning("Headline generation failed", exc_info=True)
        if not title:
            total = sum(len(s.events) for s in sections)
            title = f"Market Intelligence LATAM — Semana {self.week_number}: {total} movimentos"

        # Build metadata following SINTESE shape
        section_labels = {
            f"section_{i + 1}": s.heading for i, s in enumerate(sections)
        }

        # Flatten events for API/email rendering
        item_payload: list[dict] = []
        for s in sections:
            for scored in s.events:
                e = scored.event if hasattr(scored, "event") else scored
                item_payload.append({
                    "company_name": e.company_name,
                    "company_slug": e.company_slug,
                    "sector_slug": s.sector_slug,
                    "sector_heading": s.heading,
                    "round_type": e.round_type,
                    "amount_usd": e.amount_usd,
                    "country": e.country,
                    "city": e.city,
                    "investors": e.investors,
                    "source_url": e.source_url,
                    "source_name": e.source_name,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "editorial_score": getattr(scored, "editorial_score", None),
                    "signal_strength": getattr(scored, "signal_strength", None),
                })

        metadata = {
            "section_labels": section_labels,
            "callouts": editorial_meta.callouts if editorial_meta else [],
            "companies_mentioned": editorial_meta.companies_mentioned if editorial_meta else [],
            "topics": editorial_meta.topics if editorial_meta else [],
            "email_subject": editorial_meta.email_subject if editorial_meta else None,
            "reading_time_minutes": max(1, len(body_md.split()) // 200),
            "week_number": self.week_number,
            "items": item_payload,
            "item_count": len(item_payload),
        }

        output = AgentOutput(
            title=title,
            body_md=body_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=confidence,
            sources=[],  # DB-sourced; populated separately if needed
            content_type="NEWSLETTER",
            summary=(
                f"Market Intelligence LATAM semana {self.week_number}: "
                f"{len(item_payload)} movimentos em {len(sections)} setores."
            ),
            metadata=metadata,
        )

        logger.info("OUTPUT phase complete: %s", output.title)
        return output
