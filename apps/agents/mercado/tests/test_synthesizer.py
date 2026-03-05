"""Tests for MERCADO agent synthesizer."""

import pytest
from datetime import date

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.scorer import ScoredCompanyProfile
from apps.agents.mercado.synthesizer import synthesize_ecosystem_snapshot


def test_synthesize_empty_report():
    """Test synthesizing report with no profiles."""
    report = synthesize_ecosystem_snapshot([], week_number=7)

    assert "Sem novas startups descobertas" in report
    assert "Semana 7/2026" in report


def test_synthesize_ecosystem_snapshot():
    """Test synthesizing a complete ecosystem snapshot."""
    profile1 = CompanyProfile(
        name="BigCorp",
        slug="bigcorp",
        description="Leading fintech platform",
        sector="Fintech",
        city="São Paulo",
        country="Brasil",
        tech_stack=["Python", "React", "PostgreSQL"],
        github_url="https://github.com/bigcorp",
        source_url="https://github.com/bigcorp",
        source_name="github_sao_paulo",
    )

    profile2 = CompanyProfile(
        name="HealthStartup",
        slug="healthstartup",
        description="Telemedicine platform",
        sector="HealthTech",
        city="São Paulo",
        country="Brasil",
        tech_stack=["Node.js", "Vue"],
        source_url="https://github.com/healthstartup",
        source_name="github_sao_paulo",
    )

    profile3 = CompanyProfile(
        name="EdTechCo",
        slug="edtechco",
        description="Online learning platform",
        sector="Edtech",
        city="Rio de Janeiro",
        country="Brasil",
        tech_stack=["Python", "Django"],
        source_url="https://github.com/edtechco",
        source_name="github_rio",
    )

    confidence1 = ConfidenceScore(data_quality=0.9, analysis_confidence=0.85)
    confidence2 = ConfidenceScore(data_quality=0.7, analysis_confidence=0.65)
    confidence3 = ConfidenceScore(data_quality=0.6, analysis_confidence=0.55)

    scored = [
        ScoredCompanyProfile(profile=profile1, confidence=confidence1, composite_score=0.875),
        ScoredCompanyProfile(profile=profile2, confidence=confidence2, composite_score=0.675),
        ScoredCompanyProfile(profile=profile3, confidence=confidence3, composite_score=0.575),
    ]

    report = synthesize_ecosystem_snapshot(scored, week_number=7)

    # Verify report structure
    assert "Ecossistema LATAM" in report
    assert "Semana 7/2026" in report

    # Verify company names appear
    assert "BigCorp" in report
    assert "HealthStartup" in report
    assert "EdTechCo" in report

    # Verify sector sections
    assert "Fintech" in report
    assert "HealthTech" in report
    assert "Edtech" in report

    # Verify city distribution in panorama
    assert "São Paulo" in report
    assert "Rio de Janeiro" in report

    # Verify tech stack
    assert "Python" in report


def test_synthesize_includes_panorama_stats():
    """Test that report includes aggregate statistics in Panorama section."""
    profile = CompanyProfile(
        name="TestCo",
        slug="testco",
        description="Test company",
        sector="SaaS",
        city="São Paulo",
        country="Brasil",
        source_url="https://github.com/testco",
        source_name="github_sao_paulo",
    )

    confidence = ConfidenceScore(data_quality=0.8, analysis_confidence=0.75)
    scored = [ScoredCompanyProfile(profile=profile, confidence=confidence, composite_score=0.775)]

    report = synthesize_ecosystem_snapshot(scored, week_number=7)

    # Should include panorama section with city/sector stats
    assert "Panorama" in report
    assert "Distribuição por cidade" in report
    assert "Distribuição por setor" in report


def test_synthesize_groups_by_sector():
    """Test that report groups companies by sector."""
    profiles = [
        CompanyProfile(
            name=f"Fintech{i}",
            slug=f"fintech{i}",
            description="Payment platform",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            source_url=f"https://github.com/fintech{i}",
            source_name="github_sao_paulo",
        )
        for i in range(5)
    ]

    scored = [
        ScoredCompanyProfile(
            profile=p,
            confidence=ConfidenceScore(data_quality=0.7, analysis_confidence=0.65),
            composite_score=0.675,
        )
        for p in profiles
    ]

    report = synthesize_ecosystem_snapshot(scored, week_number=7)

    # Should show sector as section heading
    assert "## Fintech" in report
    assert "Fintech" in report
    assert "5 startups" in report or "5" in report


def test_synthesize_groups_by_city():
    """Test that report groups companies by city."""
    sao_paulo = [
        CompanyProfile(
            name=f"SP{i}",
            slug=f"sp{i}",
            description="SP company",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            source_url=f"https://github.com/sp{i}",
            source_name="github_sao_paulo",
        )
        for i in range(3)
    ]

    rio = [
        CompanyProfile(
            name=f"RJ{i}",
            slug=f"rj{i}",
            description="RJ company",
            sector="HealthTech",
            city="Rio de Janeiro",
            country="Brasil",
            source_url=f"https://github.com/rj{i}",
            source_name="github_rio",
        )
        for i in range(2)
    ]

    all_profiles = sao_paulo + rio
    scored = [
        ScoredCompanyProfile(
            profile=p,
            confidence=ConfidenceScore(data_quality=0.7, analysis_confidence=0.65),
            composite_score=0.675,
        )
        for p in all_profiles
    ]

    report = synthesize_ecosystem_snapshot(scored, week_number=7)

    # Should show city breakdown in panorama
    assert "São Paulo" in report
    assert "Rio de Janeiro" in report
    assert "3 startups" in report or "(3)" in report
    assert "2 startups" in report or "(2)" in report
