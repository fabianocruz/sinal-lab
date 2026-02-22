"""INDEX Agent — LATAM Startup Index comprehensive registry.

Discovers, deduplicates, and indexes LATAM tech startups from multiple
bulk data sources (Receita Federal, ABStartups, YC, GitHub, Crunchbase).
"""

import logging
from datetime import datetime
from typing import Any

from apps.agents.base.base_agent import BaseAgent
from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.config import AgentCategory
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.index.config import INDEX_CONFIG
from apps.agents.index.converters import convert_all
from apps.agents.index.output import generate_index_report
from apps.agents.index.pipeline import MergedCompany, run_pipeline
from apps.agents.index.scorer import score_all
from apps.agents.sources.entity_matcher import DedupIndices

logger = logging.getLogger(__name__)


class IndexAgent(BaseAgent):
    """INDEX agent for comprehensive LATAM startup registry."""

    agent_name = "index"
    agent_category = AgentCategory.DATA.value

    def __init__(self, week_number: int = 0, rf_file: str = None, api_only: bool = False):
        """Initialize INDEX agent.

        Args:
            week_number: Week number (for compatibility, not used by INDEX).
            rf_file: Optional path to Receita Federal CSV file.
            api_only: If True, skip file-based sources (RF, Crunchbase CSV).
        """
        super().__init__()
        self.week_number = week_number
        self.rf_file = rf_file
        self.api_only = api_only
        self.config = INDEX_CONFIG
        self.provenance = ProvenanceTracker()

        # Pipeline state (exposed for domain persist callback)
        self._scored_companies: list[tuple[MergedCompany, float]] = []
        self._sources_used: list[str] = []

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_id = f"index-{timestamp}"

        logger.info("Initialized INDEX agent: run_id=%s, rf_file=%s, api_only=%s", self.run_id, rf_file, api_only)

    def collect(self) -> list[Any]:
        """Collect company data from all configured sources.

        Returns:
            Dict with source_name -> list of source-specific dataclass objects.
        """
        logger.info("Starting COLLECT phase")
        collected: dict[str, list] = {}

        # Receita Federal (file-based)
        if self.rf_file and not self.api_only:
            try:
                from apps.agents.sources.receita_federal import parse_receita_csv
                rf_companies = parse_receita_csv(self.rf_file)
                if rf_companies:
                    collected["receita_federal"] = rf_companies
                    self._sources_used.append("receita_federal")
                    self.provenance.track(
                        source_url="https://dados.gov.br/dados/conjuntos-dados/cnpj",
                        source_name="receita_federal",
                        extraction_method="file",
                    )
                    logger.info("Receita Federal: %d tech companies", len(rf_companies))
            except Exception as e:
                logger.warning("Receita Federal collection failed: %s", e)

        # ABStartups API
        ab_source = self.config.get_source_by_name("abstartups")
        if ab_source and ab_source.enabled:
            try:
                import httpx
                from apps.agents.sources.abstartups import fetch_all_abstartups
                with httpx.Client(timeout=15.0) as client:
                    ab_companies = fetch_all_abstartups(
                        ab_source, client,
                        max_pages=ab_source.params.get("max_pages", 10),
                        per_page=ab_source.params.get("per_page", 50),
                    )
                if ab_companies:
                    collected["abstartups"] = ab_companies
                    self._sources_used.append("abstartups")
                    self.provenance.track(
                        source_url="https://startupbase.com.br",
                        source_name="abstartups",
                        extraction_method="api",
                    )
                    logger.info("ABStartups: %d startups", len(ab_companies))
            except Exception as e:
                logger.warning("ABStartups collection failed: %s", e)

        # YC Portfolio
        yc_source = self.config.get_source_by_name("yc_portfolio")
        if yc_source and yc_source.enabled:
            try:
                import httpx
                from apps.agents.sources.yc_portfolio import fetch_yc_companies, filter_latam
                with httpx.Client(timeout=30.0) as client:
                    all_yc = fetch_yc_companies(yc_source, client)
                    yc_companies = filter_latam(all_yc)
                if yc_companies:
                    collected["yc_portfolio"] = yc_companies
                    self._sources_used.append("yc_portfolio")
                    self.provenance.track(
                        source_url="https://www.ycombinator.com/companies",
                        source_name="yc_portfolio",
                        extraction_method="api",
                    )
                    logger.info("YC Portfolio: %d LATAM companies", len(yc_companies))
            except Exception as e:
                logger.warning("YC Portfolio collection failed: %s", e)

        # GitHub org search
        github_sources = [s for s in self.config.data_sources if "github" in s.name and s.enabled]
        if github_sources:
            try:
                from apps.agents.mercado.collector import collect_from_github
                all_github_profiles = []
                for source in github_sources:
                    profiles = collect_from_github(source, self.provenance)
                    all_github_profiles.extend(profiles)
                if all_github_profiles:
                    collected["github"] = all_github_profiles
                    self._sources_used.append("github")
                    logger.info("GitHub: %d org profiles", len(all_github_profiles))
            except Exception as e:
                logger.warning("GitHub collection failed: %s", e)

        total = sum(len(v) for v in collected.values())
        logger.info("COLLECT phase complete: %d items from %d sources", total, len(collected))
        return [collected]

    def process(self, raw_data: list[Any]) -> list[Any]:
        """Convert and deduplicate collected data through the pipeline.

        Args:
            raw_data: List containing a single dict of source_name -> items.

        Returns:
            List of MergedCompany objects.
        """
        logger.info("Starting PROCESS phase")

        if not raw_data or not raw_data[0]:
            return []

        collected = raw_data[0]

        # Convert all sources to CandidateCompany
        candidates = convert_all(
            receita_companies=collected.get("receita_federal"),
            abstartups_companies=collected.get("abstartups"),
            yc_companies=collected.get("yc_portfolio"),
            github_profiles=collected.get("github"),
            crunchbase_companies=collected.get("crunchbase"),
        )

        # Run pipeline with empty indices (no DB in process phase)
        # DB indices will be built in domain_persist_fn
        merged = run_pipeline(candidates, DedupIndices())

        logger.info("PROCESS phase complete: %d candidates -> %d merged", len(candidates), len(merged))
        return merged

    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Score merged companies.

        Args:
            processed_data: List of MergedCompany objects.

        Returns:
            List of (MergedCompany, score) tuples stored in _scored_companies.
        """
        logger.info("Starting SCORE phase with %d companies", len(processed_data))

        self._scored_companies = score_all(processed_data)

        # Return ConfidenceScore objects for the base class
        scores = []
        for merged, score in self._scored_companies:
            scores.append(ConfidenceScore(
                data_quality=round(score, 3),
                analysis_confidence=round(score * 0.9, 3),
                source_count=merged.source_count,
                verified=merged.source_count >= 2,
            ))

        logger.info("SCORE phase complete: %d companies scored", len(scores))
        return scores

    def output(self, processed_data: list[Any], scores: list[Any]) -> AgentOutput:
        """Generate INDEX report.

        Args:
            processed_data: List of MergedCompany objects (unused, data in _scored_companies).
            scores: List of ConfidenceScore objects.

        Returns:
            AgentOutput with Markdown report.
        """
        logger.info("Starting OUTPUT phase")

        output = generate_index_report(
            scored_companies=self._scored_companies,
            run_id=self.run_id,
            sources_used=self._sources_used,
        )

        logger.info("OUTPUT phase complete: %s", output.title)
        return output
