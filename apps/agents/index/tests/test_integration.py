"""Integration tests for INDEX agent — full pipeline per source.

Tests the end-to-end flow: source data -> converter -> pipeline -> merged company,
verifying sector normalization, entity matching, and multi-source dedup.
Also verifies agent-level collection for Crunchbase (enabled/skipped).
"""

import pytest
from unittest.mock import MagicMock, patch

from apps.agents.sources.entity_matcher import CandidateCompany, DedupIndices
from apps.agents.index.converters import (
    convert_all,
    from_abstartups,
    from_crunchbase,
    from_github,
    from_yc,
)
from apps.agents.index.pipeline import MergedCompany, run_pipeline


# --- ABStartups -> CandidateCompany -> MergedCompany ---


class TestABStartupsIntegration:
    def test_sector_normalized(self):
        """ABStartups Portuguese sector is normalized to canonical value."""
        from apps.agents.sources.abstartups import ABStartupsCompany

        ab = ABStartupsCompany(
            name="HealthCo",
            slug="healthco",
            sector="saúde",
            city="São Paulo",
            website="https://healthco.com.br",
        )
        candidate = from_abstartups(ab)
        assert candidate.sector == "Healthtech"

    def test_unknown_sector_preserved(self):
        """Unknown sector falls back to raw value."""
        from apps.agents.sources.abstartups import ABStartupsCompany

        ab = ABStartupsCompany(
            name="QuantumCo",
            slug="quantumco",
            sector="Quantum Computing",
            city="Campinas",
        )
        candidate = from_abstartups(ab)
        assert candidate.sector == "Quantum Computing"

    def test_full_pipeline(self):
        """ABStartups records flow through to MergedCompany correctly."""
        from apps.agents.sources.abstartups import ABStartupsCompany

        ab_list = [
            ABStartupsCompany(
                name="iFood",
                slug="ifood",
                sector="FoodTech",
                city="Campinas",
                website="https://ifood.com.br",
            ),
        ]
        candidates = convert_all(abstartups_companies=ab_list)
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].name == "iFood"
        assert merged[0].sector == "Agritech"  # FoodTech -> Agritech via alias


# --- YC -> CandidateCompany -> MergedCompany ---


class TestYCIntegration:
    def test_sector_normalized(self):
        """YC vertical is normalized to canonical sector."""
        from apps.agents.sources.yc_portfolio import YCCompany

        yc = YCCompany(
            name="Neon",
            slug="neon",
            batch="W19",
            vertical="Fintech",
            country="Brazil",
            website="https://neon.com.br",
        )
        candidate = from_yc(yc)
        assert candidate.sector == "Fintech"

    def test_developer_tools_maps_to_saas(self):
        """YC 'Developer Tools' vertical maps to SaaS."""
        from apps.agents.sources.yc_portfolio import YCCompany

        yc = YCCompany(
            name="DevCo",
            slug="devco",
            batch="S21",
            vertical="Developer Tools",
            country="Brazil",
        )
        candidate = from_yc(yc)
        assert candidate.sector == "SaaS"

    def test_full_pipeline(self):
        from apps.agents.sources.yc_portfolio import YCCompany

        yc_list = [
            YCCompany(
                name="Neon",
                slug="neon",
                batch="W19",
                vertical="Fintech",
                country="Brazil",
                website="https://neon.com.br",
            ),
        ]
        candidates = convert_all(yc_companies=yc_list)
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].name == "Neon"
        assert merged[0].sector == "Fintech"
        assert "W19" in merged[0].tags


# --- GitHub -> CandidateCompany -> MergedCompany ---


class TestGitHubIntegration:
    def test_sector_normalized(self):
        """GitHub profile sector gets normalized."""
        from apps.agents.sources.github_orgs import CompanyProfile

        profile = CompanyProfile(
            name="FinCo",
            slug="finco",
            sector="financial services",
            city="São Paulo",
            country="Brasil",
            github_url="https://github.com/finco",
            source_url="https://github.com/finco",
            source_name="github_sao_paulo",
        )
        candidate = from_github(profile)
        assert candidate.sector == "Fintech"

    def test_none_sector_stays_none(self):
        """GitHub profile with no sector stays None."""
        from apps.agents.sources.github_orgs import CompanyProfile

        profile = CompanyProfile(
            name="RandomCo",
            slug="randomco",
            city="Rio de Janeiro",
            github_url="https://github.com/randomco",
            source_url="https://github.com/randomco",
            source_name="github_rio",
        )
        candidate = from_github(profile)
        assert candidate.sector is None

    def test_full_pipeline(self):
        from apps.agents.sources.github_orgs import CompanyProfile

        profiles = [
            CompanyProfile(
                name="Nubank",
                slug="nubank",
                city="São Paulo",
                country="Brasil",
                github_url="https://github.com/nubank",
                source_url="https://github.com/nubank",
                source_name="github_sao_paulo",
            ),
        ]
        candidates = convert_all(github_profiles=profiles)
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].name == "Nubank"
        assert merged[0].github_login == "nubank"


# --- Crunchbase -> CandidateCompany -> MergedCompany ---


class TestCrunchbaseIntegration:
    def test_sector_derived_from_categories(self):
        """Crunchbase categories are used to derive sector."""
        from dataclasses import dataclass

        @dataclass
        class FakeCB:
            name: str = "PayCo"
            permalink: str = "payco"
            website_url: str = "https://payco.com"
            short_description: str = "Payments platform"
            categories: list = None
            headquarters_location: str = "São Paulo"
            founded_on: str = None

            def __post_init__(self):
                if self.categories is None:
                    self.categories = ["Financial Services", "Payments"]

        candidate = from_crunchbase(FakeCB())
        assert candidate.sector == "Fintech"

    def test_no_matching_categories_returns_none_sector(self):
        from dataclasses import dataclass

        @dataclass
        class FakeCB:
            name: str = "QuantumCo"
            permalink: str = "quantumco"
            website_url: str = "https://quantum.co"
            short_description: str = "Quantum stuff"
            categories: list = None
            founded_on: str = None

            def __post_init__(self):
                if self.categories is None:
                    self.categories = ["Quantum Computing"]

        candidate = from_crunchbase(FakeCB())
        assert candidate.sector is None

    def test_funding_fields_flow_through_pipeline(self):
        """total_funding_usd and funding_stage from Crunchbase reach MergedCompany."""
        from apps.agents.sources.crunchbase import CrunchbaseCompany

        cb = CrunchbaseCompany(
            name="Nubank",
            permalink="nubank",
            source_url="https://crunchbase.com/organization/nubank",
            source_name="crunchbase",
            total_funding_usd=700_000_000.0,
            last_equity_funding_type="series_g",
        )
        candidates = convert_all(crunchbase_companies=[cb])
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].total_funding_usd == 700_000_000.0
        assert merged[0].funding_stage == "growth"  # series_g maps to growth

    def test_from_crunchbase_passes_total_funding_usd(self):
        """from_crunchbase() forwards total_funding_usd to CandidateCompany."""
        from apps.agents.sources.crunchbase import CrunchbaseCompany

        cb = CrunchbaseCompany(
            name="Nubank",
            permalink="nubank",
            source_url="https://crunchbase.com/organization/nubank",
            source_name="crunchbase",
            total_funding_usd=700_000_000.0,
        )
        candidate = from_crunchbase(cb)
        assert candidate.total_funding_usd == 700_000_000.0

    def test_from_crunchbase_passes_funding_stage(self):
        """from_crunchbase() maps last_equity_funding_type to canonical funding_stage."""
        from apps.agents.sources.crunchbase import CrunchbaseCompany

        cb = CrunchbaseCompany(
            name="SomeCo",
            permalink="someco",
            source_url="https://crunchbase.com/organization/someco",
            source_name="crunchbase",
            last_equity_funding_type="series_b",
        )
        candidate = from_crunchbase(cb)
        assert candidate.funding_stage == "series_b"


# --- Multi-source dedup ---


class TestMultiSourceDedup:
    def test_two_sources_merge_by_domain(self):
        """Same company from ABStartups + YC merges by domain."""
        from apps.agents.sources.abstartups import ABStartupsCompany
        from apps.agents.sources.yc_portfolio import YCCompany

        ab_list = [
            ABStartupsCompany(
                name="Neon",
                slug="neon",
                sector="Fintech",
                city="São Paulo",
                website="https://neon.com.br",
            ),
        ]
        yc_list = [
            YCCompany(
                name="Neon",
                slug="neon",
                batch="W19",
                vertical="Fintech",
                country="Brazil",
                website="https://neon.com.br",
            ),
        ]

        candidates = convert_all(abstartups_companies=ab_list, yc_companies=yc_list)
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].source_count == 2
        assert set(merged[0].sources) == {"abstartups", "yc_portfolio"}

    def test_three_sources_merge(self):
        """Same company from AB + YC + GitHub merges correctly."""
        from apps.agents.sources.abstartups import ABStartupsCompany
        from apps.agents.sources.yc_portfolio import YCCompany
        from apps.agents.sources.github_orgs import CompanyProfile

        ab_list = [
            ABStartupsCompany(
                name="Neon",
                slug="neon",
                sector="Fintech",
                city="São Paulo",
                website="https://neon.com.br",
            ),
        ]
        yc_list = [
            YCCompany(
                name="Neon",
                slug="neon",
                batch="W19",
                vertical="Fintech",
                country="Brazil",
                website="https://neon.com.br",
            ),
        ]
        github_list = [
            CompanyProfile(
                name="Neon",
                slug="neon",
                website="https://neon.com.br",
                city="São Paulo",
                github_url="https://github.com/neon",
                source_url="https://github.com/neon",
                source_name="github_sao_paulo",
            ),
        ]

        candidates = convert_all(
            abstartups_companies=ab_list,
            yc_companies=yc_list,
            github_profiles=github_list,
        )
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 1
        assert merged[0].source_count == 3
        assert merged[0].sector == "Fintech"

    def test_different_companies_stay_separate(self):
        """Different companies from different sources remain separate."""
        from apps.agents.sources.abstartups import ABStartupsCompany
        from apps.agents.sources.yc_portfolio import YCCompany

        ab_list = [
            ABStartupsCompany(name="CompanyA", slug="company-a", website="https://company-a.com"),
        ]
        yc_list = [
            YCCompany(name="CompanyB", slug="company-b", website="https://company-b.com", country="Brazil"),
        ]

        candidates = convert_all(abstartups_companies=ab_list, yc_companies=yc_list)
        merged = run_pipeline(candidates, DedupIndices())

        assert len(merged) == 2


# --- Agent-level Crunchbase collection ---


class TestAgentCrunchbaseCollection:
    """Test the IndexAgent.collect() Crunchbase block."""

    def _make_agent(self):
        """Create an IndexAgent with only Crunchbase enabled."""
        from apps.agents.index.agent import IndexAgent

        agent = IndexAgent(api_only=True)
        # Disable all sources except Crunchbase API
        for src in agent.config.data_sources:
            src.enabled = src.name == "crunchbase_companies_latam"
        return agent

    @patch.dict("os.environ", {"CRUNCHBASE_API_KEY": "test-key"})
    @patch("apps.agents.sources.crunchbase.fetch_companies")
    def test_crunchbase_collected_when_api_key_set(self, mock_fetch):
        from apps.agents.sources.crunchbase import CrunchbaseCompany

        mock_fetch.return_value = [
            CrunchbaseCompany(
                name="TestCo", permalink="testco",
                source_url="https://crunchbase.com/organization/testco",
                source_name="crunchbase",
                total_funding_usd=1_000_000.0,
                last_equity_funding_type="seed",
            ),
        ]

        agent = self._make_agent()
        result = agent.collect()

        assert len(result) == 1
        collected = result[0]
        assert "crunchbase" in collected
        assert len(collected["crunchbase"]) == 1
        assert "crunchbase" in agent._sources_used

    @patch.dict("os.environ", {}, clear=True)
    def test_crunchbase_skipped_without_api_key(self):
        import os
        # Ensure key is definitely absent
        os.environ.pop("CRUNCHBASE_API_KEY", None)

        agent = self._make_agent()
        result = agent.collect()

        collected = result[0]
        assert "crunchbase" not in collected
        assert "crunchbase" not in agent._sources_used
