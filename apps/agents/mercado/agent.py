"""MERCADO Agent — LATAM startup mapping and ecosystem intelligence.

Discovers, profiles, and enriches company data to build a comprehensive
database of the LATAM tech ecosystem.
"""

import logging
from datetime import datetime
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.mercado.classifier import classify_all_profiles
from apps.agents.mercado.collector import CompanyProfile, collect_all_sources, dedup_profiles
from apps.agents.mercado.config import MERCADO_CONFIG
from apps.agents.mercado.enricher import enrich_all_profiles
from apps.agents.mercado.scorer import ScoredCompanyProfile, score_all_profiles
from apps.agents.mercado.synthesizer import synthesize_ecosystem_snapshot
from apps.agents.mercado.writer import MercadoWriter

logger = logging.getLogger(__name__)


class MercadoAgent(BaseAgent):
    """MERCADO agent for LATAM startup mapping and ecosystem intelligence."""

    agent_name = "mercado"
    agent_category = AgentCategory.DATA.value

    def __init__(self, week_number: int):
        """Initialize MERCADO agent.

        Args:
            week_number: Week number of the year (1-52)
        """
        super().__init__()
        self.week_number = week_number
        self.config = MERCADO_CONFIG
        self.provenance = ProvenanceTracker()

        # Generate run_id
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_id = f"mercado-{timestamp}"

        logger.info(
            "Initialized MERCADO agent: week=%d, run_id=%s",
            week_number,
            self.run_id,
        )

    def collect(self) -> list[Any]:
        """Collect company profiles from all configured sources.

        Returns:
            Deduplicated list of CompanyProfile objects
        """
        logger.info("Starting COLLECT phase")

        profiles = collect_all_sources(
            sources=self.config.data_sources,
            provenance=self.provenance,
        )

        # Deduplicate profiles across sources (e.g. same org from multiple city queries)
        profiles = dedup_profiles(profiles)

        logger.info("COLLECT phase complete: %d profiles after dedup", len(profiles))
        return profiles

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Process and enrich company profiles.

        Steps:
        1. Enrich with GitHub org data, website scraping, WHOIS
        2. Classify sector based on keywords
        3. Generate tags

        Args:
            raw_data: List of raw CompanyProfile objects

        Returns:
            List of processed and enriched CompanyProfile objects
        """
        logger.info("Starting PROCESS phase with %d profiles", len(raw_data))

        profiles: list[CompanyProfile] = raw_data

        # Step 1: Enrich profiles
        profiles = enrich_all_profiles(profiles)

        # Step 2: Classify sector and generate tags
        profiles = classify_all_profiles(profiles)

        # Step 3: Enrich tech_stack from Gupy job listings (if source enabled)
        gupy_source = self.config.get_source_by_name("gupy_jobs")
        if gupy_source and gupy_source.enabled:
            from apps.agents.mercado.collector import enrich_from_gupy
            profiles = enrich_from_gupy(profiles, gupy_source)

        logger.info("PROCESS phase complete: %d profiles processed", len(profiles))
        return profiles

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Score company profiles for confidence.

        Args:
            processed_data: List of processed CompanyProfile objects

        Returns:
            List of ScoredCompanyProfile objects
        """
        logger.info("Starting SCORE phase with %d profiles", len(processed_data))

        profiles: list[CompanyProfile] = processed_data
        scored_profiles = score_all_profiles(profiles)

        logger.info("SCORE phase complete: %d profiles scored", len(scored_profiles))
        return scored_profiles

    def output(
        self,
        processed_data: list[Any],
        scores: list[Any],
    ) -> AgentOutput:
        """Generate ecosystem snapshot report.

        Args:
            processed_data: List of processed CompanyProfile objects (unused)
            scores: List of ScoredCompanyProfile objects

        Returns:
            AgentOutput with Markdown ecosystem snapshot
        """
        logger.info("Starting OUTPUT phase")

        scored_profiles: list[ScoredCompanyProfile] = scores

        # Instantiate LLM writer (gracefully degrades if unavailable)
        writer = MercadoWriter()

        # Generate Markdown report with optional LLM enrichment
        body_md = synthesize_ecosystem_snapshot(
            scored_profiles, self.week_number, writer=writer
        )

        # Compute aggregate confidence
        if scored_profiles:
            avg_dq = sum(s.confidence.data_quality for s in scored_profiles) / len(scored_profiles)
            avg_ac = sum(s.confidence.analysis_confidence for s in scored_profiles) / len(scored_profiles)
            aggregate_confidence = ConfidenceScore(
                data_quality=avg_dq,
                analysis_confidence=avg_ac,
                source_count=len(self.provenance.get_sources()),
                verified=sum(1 for s in scored_profiles if s.confidence.verified) > len(scored_profiles) // 2,
            )
        else:
            aggregate_confidence = ConfidenceScore(
                data_quality=0.3,
                analysis_confidence=0.3,
            )

        # Get source URLs
        source_urls = self.provenance.get_source_urls()[:20]  # Top 20 sources

        # Generate editorial title via LLM (falls back to template)
        editorial_title = writer.write_headline(scored_profiles, self.week_number)
        if not editorial_title:
            editorial_title = f"MERCADO Report — Semana {self.week_number}/2026"

        # Extract structured per-item data for email rendering and API
        metadata = {
            "items": [
                {
                    "company_name": s.profile.name,
                    "company_slug": s.profile.slug or "",
                    "website": s.profile.website or "",
                    "sector": s.profile.sector or "",
                    "city": s.profile.city or "",
                    "country": s.profile.country,
                    "source_url": s.profile.source_url,
                    "source_name": s.profile.source_name,
                    "github_url": s.profile.github_url or "",
                    "description": (s.profile.description or "")[:200],
                    "tech_stack": s.profile.tech_stack[:5],
                }
                for s in scored_profiles[:10]
            ],
            "item_count": len(scored_profiles),
        }

        # Create output
        output = AgentOutput(
            title=editorial_title,
            body_md=body_md,
            agent_name=self.agent_name,
            agent_category=self.agent_category,
            run_id=self.run_id,
            confidence=aggregate_confidence,
            sources=source_urls,
            content_type="DATA_REPORT",
            summary=(
                f"Semana {self.week_number}: {len(scored_profiles)} organizacoes tech "
                f"descobertas no ecossistema LATAM."
            ),
            metadata=metadata,
        )

        logger.info("OUTPUT phase complete: %s", output.title)
        return output
