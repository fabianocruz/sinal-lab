"""Tests for MERCADO agent enricher."""

import pytest
from unittest.mock import Mock, patch

from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.enricher import (
    enrich_from_github_org,
    enrich_profile,
    enrich_all_profiles,
)


@pytest.fixture
def sample_profile():
    """Sample company profile for testing."""
    return CompanyProfile(
        name="TestCorp",
        slug="testcorp",
        website="https://testcorp.com",
        description="Test company",
        city="São Paulo",
        country="Brasil",
        github_url="https://github.com/testcorp",
        source_url="https://github.com/testcorp",
        source_name="github_sao_paulo",
    )


def test_enrich_profile_returns_profile(sample_profile):
    """Test that enrich_profile returns a profile (even if enrichment is not implemented)."""
    enriched = enrich_profile(sample_profile)

    assert enriched is not None
    assert enriched.name == "TestCorp"


def test_enrich_profile_without_website():
    """Test enriching profile without website."""
    profile = CompanyProfile(
        name="NoWebsite",
        slug="nowebsite",
        website=None,  # No website
        city="Rio de Janeiro",
        country="Brasil",
        source_url="https://github.com/nowebsite",
        source_name="github_rio",
    )

    enriched = enrich_profile(profile)

    assert enriched.name == "NoWebsite"


def test_enrich_profile_without_github():
    """Test enriching profile without GitHub URL."""
    profile = CompanyProfile(
        name="NoGithub",
        slug="nogithub",
        website="https://nogithub.com",
        github_url=None,  # No GitHub
        city="Mexico City",
        country="Mexico",
        source_url="https://example.com",
        source_name="dealroom_api",
    )

    enriched = enrich_profile(profile)

    assert enriched.name == "NoGithub"


def test_enrich_all_profiles():
    """Test enriching multiple profiles."""
    profiles = [
        CompanyProfile(
            name="Company1",
            slug="company1",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/company1",
            source_name="github_sao_paulo",
        ),
        CompanyProfile(
            name="Company2",
            slug="company2",
            city="Buenos Aires",
            country="Argentina",
            source_url="https://github.com/company2",
            source_name="github_buenos_aires",
        ),
    ]

    enriched = enrich_all_profiles(profiles)

    assert len(enriched) == 2
    assert enriched[0].name == "Company1"
    assert enriched[1].name == "Company2"


def test_enrich_all_profiles_handles_errors():
    """Test that enrichment errors don't crash the entire process."""
    # Create a profile that might cause errors during enrichment
    profiles = [
        CompanyProfile(
            name="ValidCompany",
            slug="valid",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/valid",
            source_name="github_sao_paulo",
        ),
    ]

    # Should not raise exception
    enriched = enrich_all_profiles(profiles)

    # Should return original profile even if enrichment fails
    assert len(enriched) == 1


# --- GitHub Org API enrichment tests ---


@patch("httpx.get")
def test_enrich_from_github_org_populates_fields(mock_get):
    """Test that GitHub org API enriches website, description, name, and founded_date."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "blog": "https://testcorp.com",
        "description": "A longer description from the org API",
        "name": "TestCorp Inc",
        "public_repos": 42,
        "created_at": "2020-03-15T00:00:00Z",
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profile = CompanyProfile(
        name="Testcorp",
        slug="testcorp",
        description="Short",
        github_url="https://github.com/testcorp",
        source_url="https://github.com/testcorp",
        source_name="github_sao_paulo",
    )

    enriched = enrich_from_github_org(profile)

    assert enriched.website == "https://testcorp.com"
    assert enriched.description == "A longer description from the org API"
    assert enriched.name == "TestCorp Inc"
    assert enriched.founded_date is not None
    assert enriched.founded_date.year == 2020


@patch("httpx.get")
def test_enrich_from_github_org_handles_404(mock_get):
    """Test graceful handling of non-existent org."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    profile = CompanyProfile(
        name="Ghost",
        slug="ghost-org",
        github_url="https://github.com/ghost-org",
        source_url="https://github.com/ghost-org",
        source_name="github_sao_paulo",
    )

    enriched = enrich_from_github_org(profile)

    assert enriched.name == "Ghost"  # unchanged


@patch("httpx.get")
def test_enrich_preserves_existing_website(mock_get):
    """Test that enricher does not overwrite existing website."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "blog": "https://github-blog.com",
        "description": "",
        "public_repos": 10,
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profile = CompanyProfile(
        name="ExistingWebsite",
        slug="existing",
        website="https://existing.com",
        github_url="https://github.com/existing",
        source_url="https://github.com/existing",
        source_name="github_sao_paulo",
    )

    enriched = enrich_from_github_org(profile)

    assert enriched.website == "https://existing.com"  # not overwritten


@patch("httpx.get")
def test_enrich_adds_https_to_bare_blog(mock_get):
    """Test that blog URLs without protocol get https:// prepended."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "blog": "testcorp.com",
        "description": "",
        "public_repos": 5,
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profile = CompanyProfile(
        name="Testcorp",
        slug="testcorp",
        github_url="https://github.com/testcorp",
        source_url="https://github.com/testcorp",
        source_name="github_sao_paulo",
    )

    enriched = enrich_from_github_org(profile)

    assert enriched.website == "https://testcorp.com"


@patch("httpx.get")
def test_enrich_keeps_shorter_description(mock_get):
    """Test that a shorter API description does not overwrite a longer existing one."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "blog": "",
        "description": "Short",
        "public_repos": 3,
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profile = CompanyProfile(
        name="Testcorp",
        slug="testcorp",
        description="This is a much longer and more detailed description of the company",
        github_url="https://github.com/testcorp",
        source_url="https://github.com/testcorp",
        source_name="github_sao_paulo",
    )

    enriched = enrich_from_github_org(profile)

    assert "much longer" in enriched.description
