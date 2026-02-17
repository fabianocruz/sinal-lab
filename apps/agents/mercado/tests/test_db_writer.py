"""Tests for MERCADO agent database writer."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, MagicMock

from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.db_writer import upsert_company, update_ecosystem_stats, persist_all_profiles


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = Mock()
    session.query = Mock(return_value=Mock())
    session.commit = Mock()
    session.rollback = Mock()
    session.add = Mock()
    return session


@pytest.fixture
def sample_company_profile():
    """Sample company profile for testing."""
    return CompanyProfile(
        name="Test Company",
        slug="test-company",
        website="https://testcompany.com",
        description="A test company",
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        founded_date=date(2020, 1, 1),
        team_size=50,
        linkedin_url="https://linkedin.com/company/test-company",
        github_url="https://github.com/test-company",
        tech_stack=["Python", "React"],
        tags=["fintech", "são-paulo", "brasil"],
        source_url="https://github.com/test-company",
        source_name="github_sao_paulo",
    )


def test_upsert_company_new_record(mock_session, sample_company_profile):
    """Test inserting new company record."""
    # Mock: no existing record
    mock_session.query().filter_by().first.return_value = None

    result = upsert_company(mock_session, sample_company_profile, confidence=0.8)

    # Should add new record
    assert mock_session.add.called
    assert mock_session.commit.called


def test_upsert_company_update_higher_confidence(mock_session, sample_company_profile):
    """Test updating existing company with higher confidence."""
    # Mock existing company with lower confidence
    existing = MagicMock()
    existing.slug = "test-company"
    existing.name = "Test Company"
    existing.description = "Old description"
    existing.website = None
    existing.metadata_ = {"confidence": 0.5}
    mock_session.query().filter_by().first.return_value = existing

    result = upsert_company(mock_session, sample_company_profile, confidence=0.8)

    # Should update existing record
    assert existing.description == "A test company"
    assert existing.website == "https://testcompany.com"
    assert existing.metadata_["confidence"] == 0.8
    assert existing.metadata_["sector"] == "Fintech"
    assert mock_session.commit.called


def test_upsert_company_skip_lower_confidence(mock_session, sample_company_profile):
    """Test skipping update when existing confidence is higher."""
    # Mock existing company with higher confidence
    existing = MagicMock()
    existing.slug = "test-company"
    existing.name = "Test Company"
    existing.description = "Existing description"
    existing.metadata_ = {"confidence": 0.9}
    mock_session.query().filter_by().first.return_value = existing

    result = upsert_company(mock_session, sample_company_profile, confidence=0.7)

    # Should NOT update (confidence lower)
    assert existing.description == "Existing description"  # Unchanged
    assert result == existing


def test_upsert_company_preserve_non_null_fields(mock_session):
    """Test that upsert preserves non-null existing fields when new data is null."""
    # Existing company with some fields
    existing = MagicMock()
    existing.slug = "preserve-test"
    existing.name = "PreserveTest"
    existing.description = "Existing description"
    existing.website = "https://existing.com"
    existing.city = "Rio de Janeiro"
    existing.country = "Brasil"
    existing.metadata_ = {"confidence": 0.6}
    mock_session.query().filter_by().first.return_value = existing

    # New profile with some null fields
    profile = CompanyProfile(
        name="PreserveTest",
        slug="preserve-test",
        description=None,  # Null - should preserve existing
        website=None,  # Null - should preserve existing
        city="São Paulo",  # Different - should update
        country="Brasil",
        source_url="https://github.com/preserve",
        source_name="github_sao_paulo",
    )

    upsert_company(mock_session, profile, confidence=0.8)

    # Should preserve non-null existing fields
    assert existing.description == "Existing description"  # Preserved
    assert existing.website == "https://existing.com"  # Preserved
    assert existing.city == "São Paulo"  # Updated (new value provided)


def test_upsert_company_without_slug(mock_session):
    """Test handling company profile without slug."""
    profile = CompanyProfile(
        name="No Slug Company",
        slug=None,  # Missing slug
        description="Test",
        city="São Paulo",
        country="Brasil",
        source_url="https://test.com",
        source_name="test",
    )

    mock_session.query().filter_by().first.return_value = None

    result = upsert_company(mock_session, profile, confidence=0.6)

    # Should still create record with generated slug
    assert mock_session.add.called
    added_company = mock_session.add.call_args[0][0]
    assert added_company.slug == "no-slug-company"


def test_update_ecosystem_stats_creates_new(mock_session):
    """Test creating new ecosystem when it doesn't exist."""
    # Mock: ecosystem doesn't exist
    mock_session.query().filter_by().first.return_value = None

    # Mock companies in the city
    company1 = MagicMock()
    company1.slug = "company1"
    company1.metadata_ = {"sector": "Fintech", "confidence": 0.8}

    company2 = MagicMock()
    company2.slug = "company2"
    company2.metadata_ = {"sector": "SaaS", "confidence": 0.7}

    mock_session.query().filter_by().all.return_value = [company1, company2]

    update_ecosystem_stats(mock_session, "São Paulo", "Brasil")

    # Should create new ecosystem
    assert mock_session.add.called
    ecosystem = mock_session.add.call_args[0][0]
    assert ecosystem.name == "São Paulo, Brasil"
    assert ecosystem.slug == "são-paulo-brasil"
    assert ecosystem.metadata_["total_startups"] == 2


def test_update_ecosystem_stats_updates_existing(mock_session):
    """Test updating existing ecosystem stats."""
    # Mock existing ecosystem
    ecosystem = MagicMock()
    ecosystem.slug = "sao-paulo-brasil"
    ecosystem.name = "São Paulo, Brasil"
    ecosystem.metadata_ = {}
    mock_session.query().filter_by().first.return_value = ecosystem

    # Mock companies
    companies = [MagicMock() for _ in range(5)]
    for i, company in enumerate(companies):
        company.slug = f"company{i}"
        company.metadata_ = {
            "sector": "Fintech" if i < 3 else "SaaS",
            "confidence": 0.8,
        }
    mock_session.query().filter_by().all.return_value = companies

    update_ecosystem_stats(mock_session, "São Paulo", "Brasil")

    # Should update stats
    assert ecosystem.metadata_["total_startups"] == 5
    assert "Fintech" in ecosystem.metadata_["top_sectors"]
    assert len(ecosystem.metadata_["notable_companies"]) > 0
    assert mock_session.commit.called


def test_update_ecosystem_stats_top_sectors_sorted(mock_session):
    """Test that top sectors are sorted by count."""
    # Mock ecosystem
    ecosystem = MagicMock()
    ecosystem.metadata_ = {}
    mock_session.query().filter_by().first.return_value = ecosystem

    # Mock companies with different sectors
    companies = []
    for i in range(10):
        company = MagicMock()
        company.slug = f"company{i}"
        if i < 5:
            sector = "Fintech"  # 5 companies
        elif i < 8:
            sector = "SaaS"  # 3 companies
        else:
            sector = "HealthTech"  # 2 companies
        company.metadata_ = {"sector": sector, "confidence": 0.8}
        companies.append(company)

    mock_session.query().filter_by().all.return_value = companies

    update_ecosystem_stats(mock_session, "São Paulo", "Brasil")

    # Top sectors should be sorted: Fintech (5), SaaS (3), HealthTech (2)
    top_sectors = ecosystem.metadata_["top_sectors"]
    assert top_sectors[0] == "Fintech"
    assert top_sectors[1] == "SaaS"
    assert top_sectors[2] == "HealthTech"


def test_update_ecosystem_stats_notable_companies_by_confidence(mock_session):
    """Test that notable companies are selected by confidence."""
    # Mock ecosystem
    ecosystem = MagicMock()
    ecosystem.metadata_ = {}
    mock_session.query().filter_by().first.return_value = ecosystem

    # Mock companies with different confidence scores
    companies = []
    for i in range(15):
        company = MagicMock()
        company.slug = f"company{i}"
        company.metadata_ = {
            "sector": "Fintech",
            "confidence": 0.5 + (i * 0.03),  # Increasing confidence
        }
        companies.append(company)

    mock_session.query().filter_by().all.return_value = companies

    update_ecosystem_stats(mock_session, "São Paulo", "Brasil")

    # Should select top 10 by confidence
    notable = ecosystem.metadata_["notable_companies"]
    assert len(notable) == 10
    # Last companies should be in notable (highest confidence)
    assert "company14" in notable
    assert "company13" in notable


def test_update_ecosystem_stats_no_companies(mock_session):
    """Test updating ecosystem with no companies."""
    # Mock existing ecosystem
    ecosystem = MagicMock()
    ecosystem.metadata_ = {}
    mock_session.query().filter_by().first.return_value = ecosystem

    # No companies
    mock_session.query().filter_by().all.return_value = []

    update_ecosystem_stats(mock_session, "Empty City", "Brasil")

    # Should not crash, ecosystem should not be updated
    # (function returns early when no companies)


def test_update_ecosystem_stats_null_city(mock_session):
    """Test handling null city gracefully."""
    update_ecosystem_stats(mock_session, None, "Brasil")

    # Should not crash, should return early
    assert not mock_session.add.called


def test_persist_all_profiles(mock_session):
    """Test persisting multiple company profiles."""
    profiles_with_confidence = [
        (
            CompanyProfile(
                name=f"Company{i}",
                slug=f"company{i}",
                city="São Paulo",
                country="Brasil",
                source_url=f"https://github.com/company{i}",
                source_name="github_sao_paulo",
            ),
            0.7 + (i * 0.05),
        )
        for i in range(3)
    ]

    # Mock: no existing companies
    mock_session.query().filter_by().count.return_value = 0
    mock_session.query().filter_by().first.return_value = None
    mock_session.query().filter_by().all.return_value = []

    stats = persist_all_profiles(mock_session, profiles_with_confidence)

    # Should insert 3 companies
    assert stats["inserted"] == 3
    assert stats["updated"] == 0
    assert stats["skipped"] == 0


def test_persist_all_profiles_mixed_operations(mock_session):
    """Test persist with mix of insert, update, and skip operations."""
    profiles_with_confidence = [
        (
            CompanyProfile(
                name="NewCo",
                slug="newco",
                city="São Paulo",
                country="Brasil",
                source_url="https://github.com/newco",
                source_name="github_sao_paulo",
            ),
            0.8,
        ),
        (
            CompanyProfile(
                name="UpdateCo",
                slug="updateco",
                city="São Paulo",
                country="Brasil",
                source_url="https://github.com/updateco",
                source_name="github_sao_paulo",
            ),
            0.9,
        ),
        (
            CompanyProfile(
                name="SkipCo",
                slug="skipco",
                city="São Paulo",
                country="Brasil",
                source_url="https://github.com/skipco",
                source_name="github_sao_paulo",
            ),
            0.5,
        ),
    ]

    # Mock different scenarios for each company
    def mock_count(slug):
        if slug == "newco":
            return 0  # New
        else:
            return 1  # Existing

    def mock_first(slug):
        if slug == "newco":
            return None  # New
        elif slug == "updateco":
            existing = MagicMock()
            existing.metadata_ = {"confidence": 0.7}  # Will be updated
            return existing
        else:  # skipco
            existing = MagicMock()
            existing.metadata_ = {"confidence": 0.9}  # Will be skipped
            return existing

    # Mock company queries (upsert_company calls)
    mock_session.query().filter_by().count.side_effect = [0, 1, 1]
    # Each upsert needs one first() call, plus update_ecosystem_stats needs first() calls
    # 3 upserts + 3 ecosystem lookups = 6 first() calls minimum
    mock_session.query().filter_by().first.side_effect = [
        None,  # newco - upsert
        None,  # ecosystem lookup for newco
        MagicMock(metadata_={"confidence": 0.7}),  # updateco - upsert
        None,  # ecosystem lookup for updateco
        MagicMock(metadata_={"confidence": 0.9}),  # skipco - upsert
        None,  # ecosystem lookup for skipco
    ]
    # All ecosystem stats queries return empty (no companies to aggregate)
    mock_session.query().filter_by().all.return_value = []

    stats = persist_all_profiles(mock_session, profiles_with_confidence)

    # Should have mixed results
    assert stats["inserted"] == 1  # newco
    assert stats["updated"] == 1  # updateco
    assert stats["skipped"] == 1  # skipco
