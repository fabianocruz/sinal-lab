"""Tests for MERCADO agent synthesizer — editorial report redesign.

Tests the section-based synthesis: select_top_profiles, group_by_sector,
format_profile_markdown, and the restructured synthesize_ecosystem_snapshot.
"""

from typing import Optional

import pytest
from unittest.mock import MagicMock

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.mercado.scorer import ScoredCompanyProfile
from apps.agents.mercado.synthesizer import (
    SectorSection,
    format_profile_markdown,
    group_by_sector,
    select_top_profiles,
    synthesize_ecosystem_snapshot,
)


def _profile(
    name: str,
    sector: str = "Fintech",
    city: str = "São Paulo",
    country: str = "Brasil",
    website: Optional[str] = None,
    github_url: Optional[str] = None,
    description: Optional[str] = "A startup description.",
    composite: float = 0.7,
) -> ScoredCompanyProfile:
    """Helper to create scored profiles with minimal boilerplate."""
    profile = CompanyProfile(
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=description,
        sector=sector,
        city=city,
        country=country,
        website=website,
        github_url=github_url,
        tech_stack=["Python", "React"],
        source_url=f"https://github.com/{name.lower()}",
        source_name="github_test",
    )
    dq = min(composite + 0.05, 1.0)
    ac = max(composite - 0.05, 0.0)
    return ScoredCompanyProfile(
        profile=profile,
        confidence=ConfidenceScore(data_quality=dq, analysis_confidence=ac),
        composite_score=composite,
    )


# --- select_top_profiles ---


class TestSelectTopProfiles:
    """Tests for select_top_profiles with diversity constraints."""

    def test_returns_up_to_count(self):
        # Use diverse cities/sectors to avoid hitting diversity caps
        cities = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Florianópolis"]
        sectors = ["Fintech", "HealthTech", "EdTech", "DevTools"]
        profiles = [
            _profile(f"Co{i}", city=cities[i % len(cities)], sector=sectors[i % len(sectors)])
            for i in range(20)
        ]
        result = select_top_profiles(profiles, count=15)
        assert len(result) == 15

    def test_returns_all_when_fewer_than_count(self):
        cities = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Florianópolis"]
        profiles = [_profile(f"Co{i}", city=cities[i % len(cities)]) for i in range(5)]
        result = select_top_profiles(profiles, count=15)
        assert len(result) == 5

    def test_sector_diversity_cap(self):
        """No single sector should have more than max_per_sector profiles."""
        # 10 Fintech + 5 HealthTech + 5 EdTech
        profiles = (
            [_profile(f"Fin{i}", sector="Fintech", composite=0.9 - i * 0.01) for i in range(10)]
            + [_profile(f"Health{i}", sector="HealthTech", composite=0.8 - i * 0.01) for i in range(5)]
            + [_profile(f"Ed{i}", sector="EdTech", composite=0.7 - i * 0.01) for i in range(5)]
        )
        result = select_top_profiles(profiles, count=15, max_per_sector=5)

        sector_counts: dict[str, int] = {}
        for s in result:
            sector = s.profile.sector or "Outros"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        assert sector_counts["Fintech"] <= 5

    def test_city_diversity_cap(self):
        """No single city should have more than max_per_city profiles."""
        profiles = (
            [_profile(f"SP{i}", city="São Paulo", composite=0.9 - i * 0.01) for i in range(10)]
            + [_profile(f"RJ{i}", city="Rio de Janeiro", composite=0.8 - i * 0.01) for i in range(5)]
        )
        result = select_top_profiles(profiles, count=15, max_per_city=4)

        city_counts: dict[str, int] = {}
        for s in result:
            city = s.profile.city or "N/A"
            city_counts[city] = city_counts.get(city, 0) + 1

        assert city_counts["São Paulo"] <= 4

    def test_preserves_input_ordering(self):
        """Profiles are selected in input order (pre-sorted by caller)."""
        profiles = [
            _profile("High", city="São Paulo", composite=0.9),
            _profile("Mid", city="Rio de Janeiro", composite=0.6),
            _profile("Low", city="Belo Horizonte", composite=0.3),
        ]
        result = select_top_profiles(profiles, count=3)
        assert result[0].profile.name == "High"
        assert result[1].profile.name == "Mid"
        assert result[2].profile.name == "Low"

    def test_empty_input(self):
        result = select_top_profiles([], count=15)
        assert result == []


# --- group_by_sector ---


class TestGroupBySector:
    """Tests for group_by_sector."""

    def test_groups_correctly(self):
        profiles = [
            _profile("Fin1", sector="Fintech"),
            _profile("Fin2", sector="Fintech"),
            _profile("Health1", sector="HealthTech"),
        ]
        sections = group_by_sector(profiles)

        assert len(sections) == 2
        names = {s.heading for s in sections}
        assert "Fintech" in names
        assert "HealthTech" in names

    def test_sorted_by_size_descending(self):
        profiles = [
            _profile("Ed1", sector="EdTech"),
            _profile("Fin1", sector="Fintech"),
            _profile("Fin2", sector="Fintech"),
            _profile("Fin3", sector="Fintech"),
            _profile("Ed2", sector="EdTech"),
        ]
        sections = group_by_sector(profiles)

        assert sections[0].heading == "Fintech"
        assert len(sections[0].profiles) == 3
        assert sections[1].heading == "EdTech"
        assert len(sections[1].profiles) == 2

    def test_none_sector_grouped_as_outros(self):
        profiles = [_profile("Co1", sector=None)]
        # CompanyProfile.sector is Optional[str], but _profile sets it
        profiles[0].profile.sector = None
        sections = group_by_sector(profiles)

        assert len(sections) == 1
        assert sections[0].heading == "Outros"

    def test_empty_input(self):
        sections = group_by_sector([])
        assert sections == []


# --- format_profile_markdown ---


class TestFormatProfileMarkdown:
    """Tests for format_profile_markdown."""

    def test_includes_linked_name_with_website(self):
        scored = _profile("NuPay", website="https://nupay.com")
        md = format_profile_markdown(scored, index=1)
        assert "[NuPay](https://nupay.com)" in md

    def test_includes_linked_name_with_github_fallback(self):
        scored = _profile("NuPay", github_url="https://github.com/nupay")
        md = format_profile_markdown(scored, index=1)
        assert "[NuPay](https://github.com/nupay)" in md

    def test_includes_unlinked_name_when_no_url(self):
        scored = _profile("NuPay")
        md = format_profile_markdown(scored, index=1)
        assert "**1. NuPay**" in md

    def test_includes_city_and_sector(self):
        scored = _profile("NuPay", city="São Paulo", sector="Fintech")
        md = format_profile_markdown(scored, index=1)
        assert "São Paulo" in md
        assert "Fintech" in md

    def test_includes_tech_stack(self):
        scored = _profile("NuPay")
        md = format_profile_markdown(scored, index=1)
        assert "Python" in md
        assert "React" in md

    def test_includes_github_link(self):
        scored = _profile("NuPay", github_url="https://github.com/nupay")
        md = format_profile_markdown(scored, index=1)
        assert "https://github.com/nupay" in md

    def test_uses_description_override(self):
        scored = _profile("NuPay")
        md = format_profile_markdown(
            scored, index=1, description_override="LLM-generated editorial text."
        )
        assert "LLM-generated editorial text." in md
        assert "A startup description." not in md

    def test_falls_back_to_original_description(self):
        scored = _profile("NuPay", description="Original description text.")
        md = format_profile_markdown(scored, index=1)
        assert "Original description text." in md

    def test_handles_missing_description(self):
        scored = _profile("NuPay", description=None)
        md = format_profile_markdown(scored, index=1)
        assert "NuPay" in md  # Should not crash


# --- synthesize_ecosystem_snapshot (restructured) ---


class TestSynthesizeEcosystemSnapshot:
    """Tests for the restructured synthesize_ecosystem_snapshot."""

    def test_empty_profiles(self):
        report = synthesize_ecosystem_snapshot([], week_number=10)
        assert "Sem novas startups descobertas" in report

    def test_report_has_section_structure(self):
        """Report should have sector sections instead of flat highlights."""
        profiles = [
            _profile("Fin1", sector="Fintech", composite=0.9),
            _profile("Fin2", sector="Fintech", composite=0.85),
            _profile("Health1", sector="HealthTech", composite=0.8),
        ]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10)

        assert "## Fintech" in report
        assert "## HealthTech" in report

    def test_report_has_aggregate_stats(self):
        """Report should include city/sector aggregate stats."""
        profiles = [
            _profile(f"Co{i}", sector="Fintech", city="São Paulo") for i in range(5)
        ] + [
            _profile(f"RJ{i}", sector="HealthTech", city="Rio de Janeiro") for i in range(3)
        ]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10)

        assert "Panorama" in report or "Ecossistema" in report
        assert "São Paulo" in report
        assert "Rio de Janeiro" in report

    def test_report_includes_profile_links(self):
        """Profiles with websites should have linked names."""
        profiles = [
            _profile("NuPay", website="https://nupay.com", composite=0.9),
        ]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10)
        assert "[NuPay](https://nupay.com)" in report

    def test_report_with_writer(self):
        """When writer is available, report includes LLM content."""
        mock_writer = MagicMock()
        mock_writer.is_available = True
        mock_writer.write_snapshot_intro.return_value = "LLM-generated intro paragraph."
        mock_writer.write_sector_analysis.return_value = MagicMock(
            intro="Fintech sector analysis.",
            descriptions=["NuPay leads in payments.", "PayCo innovates in credit."],
        )

        profiles = [
            _profile("NuPay", sector="Fintech", composite=0.9),
            _profile("PayCo", sector="Fintech", composite=0.85),
        ]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10, writer=mock_writer)

        assert "LLM-generated intro paragraph." in report
        assert "Fintech sector analysis." in report
        assert "NuPay leads in payments." in report

    def test_report_without_writer_uses_templates(self):
        """Without writer, report uses template-based descriptions."""
        profiles = [
            _profile("NuPay", sector="Fintech", description="A payments platform."),
        ]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10, writer=None)

        assert "NuPay" in report
        assert "A payments platform." in report

    def test_report_header_and_footer(self):
        profiles = [_profile("Co1")]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10)

        assert "Semana 10/2026" in report
        assert "Sinal.lab" in report or "sinal" in report.lower()

    def test_template_mode_notice_when_no_writer(self):
        profiles = [_profile("Co1")]
        report = synthesize_ecosystem_snapshot(profiles, week_number=10, writer=None)

        assert "template" in report.lower() or "ANTHROPIC_API_KEY" in report
