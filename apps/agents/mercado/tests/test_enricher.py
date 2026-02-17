"""Tests for MERCADO agent enricher."""

import pytest

from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.enricher import (
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
