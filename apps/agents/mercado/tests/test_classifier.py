"""Tests for MERCADO agent classifier."""

import pytest

from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.classifier import (
    classify_sector,
    generate_tags,
    classify_all_profiles,
)


def test_classify_sector_fintech():
    """Test classification of fintech company."""
    profile = CompanyProfile(
        name="PaymentCo",
        slug="paymentco",
        description="Digital payment platform for small businesses",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/paymentco",
        source_name="github_sao_paulo",
    )

    sector = classify_sector(profile)

    assert sector == "Fintech"


def test_classify_sector_healthtech():
    """Test classification of healthtech company."""
    profile = CompanyProfile(
        name="HealthApp",
        slug="healthapp",
        description="Telemedicine platform connecting patients with doctors",
        city="Rio de Janeiro",
        country="Brasil",
        source_url="https://github.com/healthapp",
        source_name="github_rio",
    )

    sector = classify_sector(profile)

    assert sector == "HealthTech"


def test_classify_sector_edtech():
    """Test classification of edtech company."""
    profile = CompanyProfile(
        name="LearnPlatform",
        slug="learnplatform",
        description="Online education platform for students and teachers",
        city="Bogotá",
        country="Colombia",
        source_url="https://github.com/learnplatform",
        source_name="github_bogota",
    )

    sector = classify_sector(profile)

    assert sector == "Edtech"


def test_classify_sector_saas():
    """Test classification of SaaS company."""
    profile = CompanyProfile(
        name="CloudSoft",
        slug="cloudsoft",
        description="Enterprise cloud software platform for automation",
        city="Mexico City",
        country="Mexico",
        source_url="https://github.com/cloudsoft",
        source_name="github_mexico_city",
    )

    sector = classify_sector(profile)

    assert sector == "SaaS"


def test_classify_sector_multiple_keywords():
    """Test classification when multiple keywords match (should return highest score)."""
    profile = CompanyProfile(
        name="FinHealthCo",
        slug="finhealthco",
        description="Financial services for healthcare providers and hospitals",
        city="Buenos Aires",
        country="Argentina",
        source_url="https://github.com/finhealthco",
        source_name="github_buenos_aires",
    )

    sector = classify_sector(profile)

    # Should match either Fintech or HealthTech (whichever has more keywords)
    assert sector in ["Fintech", "HealthTech"]


def test_classify_sector_no_match():
    """Test classification when no keywords match."""
    profile = CompanyProfile(
        name="GenericCo",
        slug="genericco",
        description="A company that does things",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/genericco",
        source_name="github_sao_paulo",
    )

    sector = classify_sector(profile)

    assert sector is None


def test_classify_sector_no_description():
    """Test classification when description is missing."""
    profile = CompanyProfile(
        name="NoDesc",
        slug="nodesc",
        description=None,
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/nodesc",
        source_name="github_sao_paulo",
    )

    sector = classify_sector(profile)

    assert sector is None


def test_generate_tags_with_sector():
    """Test tag generation with sector."""
    profile = CompanyProfile(
        name="TechCo",
        slug="techco",
        description="Payment platform",
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        tech_stack=["Python", "React"],
        source_url="https://github.com/techco",
        source_name="github_sao_paulo",
    )

    tags = generate_tags(profile)

    assert "fintech" in tags
    assert "python" in tags
    assert "react" in tags
    assert "são-paulo" in tags
    assert "brasil" in tags


def test_generate_tags_no_duplicates():
    """Test that tag generation removes duplicates."""
    profile = CompanyProfile(
        name="TechCo",
        slug="techco",
        sector="SaaS",
        city="São Paulo",
        country="Brasil",
        tech_stack=["Python", "Python"],  # Duplicate
        source_url="https://github.com/techco",
        source_name="github_sao_paulo",
    )

    tags = generate_tags(profile)

    # Should only have one "python" tag
    assert tags.count("python") == 1


def test_classify_all_profiles():
    """Test classifying multiple profiles."""
    profiles = [
        CompanyProfile(
            name="FinCo",
            slug="finco",
            description="Digital banking platform",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/finco",
            source_name="github_sao_paulo",
        ),
        CompanyProfile(
            name="HealthCo",
            slug="healthco",
            description="Telemedicine app",
            city="Rio de Janeiro",
            country="Brasil",
            source_url="https://github.com/healthco",
            source_name="github_rio",
        ),
    ]

    classified = classify_all_profiles(profiles)

    assert len(classified) == 2
    assert classified[0].sector == "Fintech"
    assert classified[1].sector == "HealthTech"
    assert len(classified[0].tags) > 0
    assert len(classified[1].tags) > 0
