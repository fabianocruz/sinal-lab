"""Integration tests between FUNDING and MERCADO agents.

Tests cross-agent scenarios where both agents interact with shared database
tables (Company, Ecosystem) to ensure data consistency and proper merging.
"""

import pytest
from datetime import date
from unittest.mock import Mock
from uuid import uuid4

from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.db_writer import upsert_funding_round, update_company_funding_stats
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.db_writer import upsert_company, update_ecosystem_stats
from packages.database.models.company import Company
from packages.database.models.funding_round import FundingRound
from packages.database.models.ecosystem import Ecosystem


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session for database operations."""
    session = Mock()
    session.query = Mock(return_value=Mock())
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


class TestFundingMercadoIntegration:
    """Test integration between FUNDING and MERCADO agents."""

    def test_funding_creates_company_reference(self, mock_session):
        """Test that FUNDING creates valid company_slug references."""
        # FUNDING discovers a funding round for a new company
        funding_event = FundingEvent(
            company_name="NewStartup",
            company_slug="newstartup",
            round_type="series_a",
            amount_usd=10.0,
            currency="USD",
            announced_date=date(2026, 2, 15),
            source_url="https://test.com/funding",
            source_name="test_source",
        )

        # Mock: no existing funding round
        mock_session.query().filter_by().first.return_value = None

        # Upsert funding round
        result = upsert_funding_round(mock_session, funding_event, confidence=0.8)

        # Verify company_slug is set correctly
        assert mock_session.add.called
        added_round = mock_session.add.call_args[0][0]
        assert added_round.company_slug == "newstartup"
        assert added_round.company_name == "NewStartup"

    def test_mercado_enriches_funded_company(self, mock_session):
        """Test that MERCADO can enrich a company discovered by FUNDING."""
        # Setup: Company already exists from FUNDING
        existing_company = Mock(spec=Company)
        existing_company.slug = "newstartup"
        existing_company.name = "NewStartup"
        existing_company.description = None  # Not set by FUNDING
        existing_company.website = None
        existing_company.city = None
        existing_company.country = "Brasil"
        existing_company.metadata_ = {
            "last_funding_date": "2026-02-15",
            "total_raised_usd": 10.0,
            "confidence": 0.5,  # Lower confidence from FUNDING
        }
        mock_session.query().filter_by().first.return_value = existing_company

        # MERCADO discovers more details about the same company
        company_profile = CompanyProfile(
            name="NewStartup",
            slug="newstartup",
            description="AI-powered fintech platform",
            website="https://newstartup.com",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            tech_stack=["Python", "React"],
            github_url="https://github.com/newstartup",
            source_url="https://github.com/newstartup",
            source_name="github_sao_paulo",
        )

        # Upsert with higher confidence
        result = upsert_company(mock_session, company_profile, confidence=0.8)

        # Verify company is enriched, not replaced
        assert existing_company.description == "AI-powered fintech platform"
        assert existing_company.website == "https://newstartup.com"
        assert existing_company.city == "São Paulo"
        # Verify funding metadata is preserved
        assert existing_company.metadata_["last_funding_date"] == "2026-02-15"
        assert existing_company.metadata_["total_raised_usd"] == 10.0

    def test_funding_updates_existing_mercado_company(self, mock_session):
        """Test that FUNDING can add funding stats to a MERCADO-discovered company."""
        # Setup: Company exists from MERCADO (no funding data yet)
        existing_company = Mock(spec=Company)
        existing_company.slug = "techcorp"
        existing_company.name = "TechCorp"
        existing_company.description = "Software company"
        existing_company.website = "https://techcorp.com"
        existing_company.city = "São Paulo"
        existing_company.country = "Brasil"
        existing_company.metadata_ = {
            "sector": "SaaS",
            "confidence": 0.7,
        }
        mock_session.query().filter_by().first.return_value = existing_company

        # Mock funding rounds query for stats update
        funding_round = Mock(spec=FundingRound)
        funding_round.announced_date = date(2026, 2, 10)
        funding_round.amount_usd = 5.0
        mock_session.query().filter_by().all.return_value = [funding_round]

        # FUNDING updates company stats
        update_company_funding_stats(mock_session, "techcorp")

        # Verify funding metadata is added
        assert "last_funding_date" in existing_company.metadata_
        assert existing_company.metadata_["total_raised_usd"] == 5.0
        assert existing_company.metadata_["funding_rounds_count"] == 1
        # Verify MERCADO data is preserved
        assert existing_company.metadata_["sector"] == "SaaS"

    def test_ecosystem_stats_include_funding_data(self, mock_session):
        """Test that MERCADO ecosystem stats correctly include funding data."""
        # Setup: Ecosystem doesn't exist yet
        mock_session.query().filter_by().first.side_effect = [
            None,  # First call: ecosystem doesn't exist
            None,  # Second call (if any)
        ]

        # Setup: Multiple companies with funding data
        company1 = Mock(spec=Company)
        company1.slug = "funded-startup"
        company1.metadata_ = {
            "sector": "Fintech",
            "confidence": 0.8,
            "total_raised_usd": 15.0,  # Has funding
        }

        company2 = Mock(spec=Company)
        company2.slug = "unfunded-startup"
        company2.metadata_ = {
            "sector": "SaaS",
            "confidence": 0.7,
            # No funding data
        }

        mock_session.query().filter_by().all.return_value = [company1, company2]

        # MERCADO updates ecosystem stats
        update_ecosystem_stats(mock_session, "São Paulo", "Brasil")

        # Verify ecosystem was created
        assert mock_session.add.called
        ecosystem = mock_session.add.call_args[0][0]
        assert ecosystem.name == "São Paulo, Brasil"
        assert ecosystem.metadata_["total_startups"] == 2
        assert "Fintech" in ecosystem.metadata_["top_sectors"]
        assert "funded-startup" in ecosystem.metadata_["notable_companies"]

    def test_concurrent_updates_preserve_data(self, mock_session):
        """Test that concurrent updates from both agents preserve all data."""
        # Scenario: FUNDING and MERCADO update the same company in sequence

        # Initial state: minimal company from FUNDING
        company = Mock(spec=Company)
        company.slug = "concurrent-test"
        company.name = "ConcurrentTest"
        company.description = None
        company.website = None
        company.city = None
        company.country = "Brasil"
        company.metadata_ = {
            "last_funding_date": "2026-02-01",
            "total_raised_usd": 5.0,
            "confidence": 0.6,
        }
        mock_session.query().filter_by().first.return_value = company

        # Step 1: MERCADO enriches with higher confidence
        mercado_profile = CompanyProfile(
            name="ConcurrentTest",
            slug="concurrent-test",
            description="Updated description",
            website="https://concurrent.com",
            sector="Fintech",
            city="Rio de Janeiro",
            country="Brasil",
            source_url="https://github.com/concurrent",
            source_name="github_rio",
        )
        upsert_company(mock_session, mercado_profile, confidence=0.8)

        # Verify MERCADO added data
        assert company.description == "Updated description"
        assert company.website == "https://concurrent.com"
        assert company.city == "Rio de Janeiro"
        # Funding data should be preserved
        assert company.metadata_["last_funding_date"] == "2026-02-01"
        assert company.metadata_["total_raised_usd"] == 5.0
        # Confidence should be updated
        assert company.metadata_["confidence"] == 0.8

    def test_slug_consistency_across_agents(self, mock_session):
        """Test that both agents generate consistent slugs for the same company."""
        # FUNDING creates slug from company name
        funding_event = FundingEvent(
            company_name="Test Company Inc",
            company_slug=None,  # Will be generated
            round_type="seed",
            amount_usd=2.0,
            currency="USD",
            announced_date=date(2026, 2, 15),
            source_url="https://test.com",
            source_name="test",
        )

        mock_session.query().filter_by().first.return_value = None
        upsert_funding_round(mock_session, funding_event, confidence=0.7)

        # Get the generated slug
        added_round = mock_session.add.call_args[0][0]
        funding_slug = added_round.company_slug

        # MERCADO should generate the same slug
        mercado_profile = CompanyProfile(
            name="Test Company Inc",
            slug=None,  # Will be generated
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/test-company",
            source_name="github_sao_paulo",
        )

        # Both should normalize to the same slug
        assert funding_slug == "test-company-inc"
        # MERCADO would generate the same
        assert mercado_profile.name.lower().replace(" ", "-") == "test-company-inc"

    def test_funding_without_company_creates_minimal_record(self, mock_session):
        """Test that FUNDING can work even without MERCADO data."""
        # FUNDING processes a round for unknown company
        funding_event = FundingEvent(
            company_name="Unknown Startup",
            company_slug="unknown-startup",
            round_type="series_a",
            amount_usd=8.0,
            currency="USD",
            announced_date=date(2026, 2, 15),
            lead_investors=["VC Fund"],
            source_url="https://test.com/unknown",
            source_name="test_source",
        )

        # No existing funding round
        mock_session.query().filter_by().first.return_value = None

        # Upsert funding round
        result = upsert_funding_round(mock_session, funding_event, confidence=0.7)

        # Verify funding round created with minimal company info
        assert mock_session.add.called
        added_round = mock_session.add.call_args[0][0]
        assert added_round.company_slug == "unknown-startup"
        assert added_round.company_name == "Unknown Startup"
        assert added_round.amount_usd == 8.0

    def test_mercado_handles_companies_with_funding(self, mock_session):
        """Test that MERCADO correctly handles companies that already have funding data."""
        # Setup: Company with funding history
        existing_company = Mock(spec=Company)
        existing_company.slug = "funded-co"
        existing_company.name = "FundedCo"
        existing_company.description = None
        existing_company.metadata_ = {
            "last_funding_date": "2026-01-15",
            "total_raised_usd": 20.0,
            "funding_rounds_count": 2,
            "confidence": 0.7,
        }
        mock_session.query().filter_by().first.return_value = existing_company

        # MERCADO enriches with company details
        mercado_profile = CompanyProfile(
            name="FundedCo",
            slug="funded-co",
            description="Well-funded startup",
            website="https://fundedco.com",
            sector="HealthTech",
            city="São Paulo",
            country="Brasil",
            tech_stack=["Python", "Django"],
            source_url="https://github.com/fundedco",
            source_name="github_sao_paulo",
        )

        # Upsert with high confidence
        upsert_company(mock_session, mercado_profile, confidence=0.85)

        # Verify enrichment preserves funding data
        assert existing_company.description == "Well-funded startup"
        assert existing_company.website == "https://fundedco.com"
        assert existing_company.metadata_["sector"] == "HealthTech"
        # Critical: funding data must be preserved
        assert existing_company.metadata_["last_funding_date"] == "2026-01-15"
        assert existing_company.metadata_["total_raised_usd"] == 20.0
        assert existing_company.metadata_["funding_rounds_count"] == 2
        # Confidence updated to higher value
        assert existing_company.metadata_["confidence"] == 0.85


class TestCrossAgentDataFlow:
    """Test data flow scenarios across multiple agent runs."""

    def test_weekly_agent_sequence(self, mock_session):
        """Test typical weekly sequence: FUNDING (Mon) → MERCADO (Wed)."""
        # Monday: FUNDING discovers new round
        funding_event = FundingEvent(
            company_name="WeeklyTest",
            company_slug="weeklytest",
            round_type="seed",
            amount_usd=3.0,
            currency="USD",
            announced_date=date(2026, 2, 17),  # Monday
            source_url="https://test.com/weekly",
            source_name="test_source",
        )

        # No existing data
        mock_session.query().filter_by().first.return_value = None
        upsert_funding_round(mock_session, funding_event, confidence=0.75)

        # Verify funding round created
        added_round = mock_session.add.call_args[0][0]
        assert added_round.company_slug == "weeklytest"

        # Wednesday: MERCADO discovers same company on GitHub
        # Setup: Company now exists with funding data
        existing_company = Mock(spec=Company)
        existing_company.slug = "weeklytest"
        existing_company.name = "WeeklyTest"
        existing_company.metadata_ = {
            "last_funding_date": "2026-02-17",
            "total_raised_usd": 3.0,
            "confidence": 0.5,
        }
        mock_session.query().filter_by().first.return_value = existing_company

        mercado_profile = CompanyProfile(
            name="WeeklyTest",
            slug="weeklytest",
            description="GitHub-discovered startup",
            sector="SaaS",
            city="São Paulo",
            country="Brasil",
            github_url="https://github.com/weeklytest",
            source_url="https://github.com/weeklytest",
            source_name="github_sao_paulo",
        )

        upsert_company(mock_session, mercado_profile, confidence=0.8)

        # Verify complete company profile
        assert existing_company.description == "GitHub-discovered startup"
        assert existing_company.metadata_["sector"] == "SaaS"
        # Funding data preserved from Monday
        assert existing_company.metadata_["last_funding_date"] == "2026-02-17"
        assert existing_company.metadata_["total_raised_usd"] == 3.0
