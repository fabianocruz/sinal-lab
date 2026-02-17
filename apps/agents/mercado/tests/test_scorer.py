"""Tests for MERCADO agent scorer."""

import pytest
from datetime import date

from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.scorer import (
    compute_field_completeness,
    score_single_profile,
    score_all_profiles,
)


@pytest.fixture
def complete_profile():
    """Profile with all fields filled."""
    return CompanyProfile(
        name="CompleteCo",
        slug="completeco",
        website="https://completeco.com",
        description="Complete company profile",
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        founded_date=date(2020, 1, 1),
        team_size=50,
        linkedin_url="https://linkedin.com/company/completeco",
        github_url="https://github.com/completeco",
        tech_stack=["Python", "React"],
        source_url="https://api.dealroom.co/completeco",
        source_name="dealroom_api",
    )


@pytest.fixture
def minimal_profile():
    """Profile with only required fields."""
    return CompanyProfile(
        name="MinimalCo",
        slug="minimalco",
        city="Rio de Janeiro",
        country="Brasil",
        source_url="https://github.com/minimalco",
        source_name="github_rio",
    )


def test_compute_field_completeness_complete(complete_profile):
    """Test field completeness for complete profile."""
    completeness = compute_field_completeness(complete_profile)

    # All 12 fields should be filled
    assert completeness == 1.0


def test_compute_field_completeness_minimal(minimal_profile):
    """Test field completeness for minimal profile."""
    completeness = compute_field_completeness(minimal_profile)

    # Only 4 fields filled: name, slug, city, country
    # (source fields don't count in completeness)
    assert completeness == 4 / 12  # 0.333...


def test_score_single_profile_complete(complete_profile):
    """Test scoring a complete profile."""
    scored = score_single_profile(complete_profile)

    assert scored.profile.name == "CompleteCo"
    # High completeness + API source + has description + has sector = high confidence
    assert scored.confidence.data_quality > 0.8
    assert scored.confidence.analysis_confidence > 0.6
    assert scored.composite_score > 0.7


def test_score_single_profile_minimal(minimal_profile):
    """Test scoring a minimal profile."""
    scored = score_single_profile(minimal_profile)

    assert scored.profile.name == "MinimalCo"
    # Low completeness + no description + no sector = low confidence
    assert scored.confidence.data_quality < 0.5
    assert scored.confidence.analysis_confidence < 0.7


def test_score_single_profile_no_description_penalty():
    """Test that missing description reduces confidence."""
    profile = CompanyProfile(
        name="NoDesc",
        slug="nodesc",
        description=None,  # Missing description
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/nodesc",
        source_name="github_sao_paulo",
    )

    scored = score_single_profile(profile)

    # Should have DQ penalty for missing description
    assert scored.confidence.data_quality < 0.5


def test_score_single_profile_no_sector_penalty():
    """Test that missing sector reduces confidence."""
    profile = CompanyProfile(
        name="NoSector",
        slug="nosector",
        description="A company",
        sector=None,  # Missing sector
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/nosector",
        source_name="github_sao_paulo",
    )

    scored = score_single_profile(profile)

    # Should have DQ penalty for missing sector
    assert scored.confidence.data_quality < 0.7


def test_score_single_profile_api_source_boost():
    """Test that API sources get confidence boost."""
    api_profile = CompanyProfile(
        name="APICo",
        slug="apico",
        description="API sourced company",
        city="São Paulo",
        country="Brasil",
        source_url="https://api.dealroom.co/apico",
        source_name="dealroom_api",  # API source
    )

    github_profile = CompanyProfile(
        name="GitHubCo",
        slug="githubco",
        description="GitHub sourced company",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/githubco",
        source_name="github_sao_paulo",  # GitHub source
    )

    api_scored = score_single_profile(api_profile)
    github_scored = score_single_profile(github_profile)

    # API source should have higher DQ due to boost
    assert api_scored.confidence.data_quality > github_scored.confidence.data_quality


def test_score_single_profile_long_description_boost():
    """Test that longer descriptions increase AC."""
    short_desc = CompanyProfile(
        name="ShortDesc",
        slug="shortdesc",
        description="Short",  # < 100 chars
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/shortdesc",
        source_name="github_sao_paulo",
    )

    long_desc = CompanyProfile(
        name="LongDesc",
        slug="longdesc",
        description="A" * 150,  # > 100 chars
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/longdesc",
        source_name="github_sao_paulo",
    )

    short_scored = score_single_profile(short_desc)
    long_scored = score_single_profile(long_desc)

    # Longer description should have higher AC
    assert long_scored.confidence.analysis_confidence > short_scored.confidence.analysis_confidence


def test_score_all_profiles():
    """Test scoring multiple profiles."""
    profiles = [
        CompanyProfile(
            name="HighConf",
            slug="highconf",
            website="https://highconf.com",
            description="Complete profile with all data",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            founded_date=date(2020, 1, 1),
            team_size=100,
            source_url="https://api.dealroom.co/highconf",
            source_name="dealroom_api",
        ),
        CompanyProfile(
            name="LowConf",
            slug="lowconf",
            city="Rio de Janeiro",
            country="Brasil",
            source_url="https://github.com/lowconf",
            source_name="github_rio",
        ),
    ]

    scored = score_all_profiles(profiles)

    # Should return 2 scored profiles
    assert len(scored) == 2

    # Should be sorted by confidence (highest first)
    assert scored[0].composite_score >= scored[1].composite_score
    assert scored[0].profile.name == "HighConf"
    assert scored[1].profile.name == "LowConf"


def test_score_all_profiles_empty():
    """Test scoring empty list."""
    scored = score_all_profiles([])

    assert scored == []
