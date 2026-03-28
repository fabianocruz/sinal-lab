"""Tests for MERCADO entity deduplication.

Tests _normalize_slug, _count_filled_fields, and dedup_profiles.
"""

import pytest

from apps.agents.mercado.collector import (
    CompanyProfile,
    _count_filled_fields,
    _normalize_slug,
    dedup_profiles,
)


# ---------------------------------------------------------------------------
# TestNormalizeSlug
# ---------------------------------------------------------------------------


class TestNormalizeSlug:
    """Tests for _normalize_slug()."""

    def test_basic_name(self):
        assert _normalize_slug("Nubank") == "nubank"

    def test_with_spaces(self):
        assert _normalize_slug("Stone Pagamentos") == "stone-pagamentos"

    def test_with_special_chars(self):
        assert _normalize_slug("iFood!") == "ifood"

    def test_with_mixed_case(self):
        assert _normalize_slug("MercadoLibre") == "mercadolibre"

    def test_with_leading_trailing_spaces(self):
        assert _normalize_slug("  nubank  ") == "nubank"

    def test_multiple_spaces_become_single_hyphen(self):
        assert _normalize_slug("my   company") == "my-company"

    def test_empty_string(self):
        assert _normalize_slug("") == ""


# ---------------------------------------------------------------------------
# TestCountFilledFields
# ---------------------------------------------------------------------------


class TestCountFilledFields:
    """Tests for _count_filled_fields()."""

    def test_minimal_profile(self):
        p = CompanyProfile(name="Test")
        assert _count_filled_fields(p) == 0

    def test_full_profile(self):
        p = CompanyProfile(
            name="Test",
            website="https://test.com",
            description="A company",
            sector="Fintech",
            city="São Paulo",
            github_url="https://github.com/test",
            tech_stack=["Python", "React"],
            tags=["fintech"],
        )
        # website, description, sector, city, github_url = 5
        # tech_stack: 2, tags: 1 → total = 8
        assert _count_filled_fields(p) == 8


# ---------------------------------------------------------------------------
# TestDedupProfiles
# ---------------------------------------------------------------------------


class TestDedupProfiles:
    """Tests for dedup_profiles()."""

    def test_empty_list(self):
        assert dedup_profiles([]) == []

    def test_no_duplicates(self):
        profiles = [
            CompanyProfile(name="Nubank", slug="nubank"),
            CompanyProfile(name="Stone", slug="stone"),
        ]
        result = dedup_profiles(profiles)
        assert len(result) == 2

    def test_same_name_different_case(self):
        profiles = [
            CompanyProfile(name="Nubank", slug="nubank"),
            CompanyProfile(name="nubank", slug="Nubank"),
        ]
        result = dedup_profiles(profiles)
        assert len(result) == 1

    def test_same_slug_from_different_sources(self):
        profiles = [
            CompanyProfile(name="Nubank", slug="nubank", source_name="github_sao_paulo"),
            CompanyProfile(name="Nubank", slug="nubank", source_name="github_rio"),
        ]
        result = dedup_profiles(profiles)
        assert len(result) == 1

    def test_keeps_most_complete_profile(self):
        sparse = CompanyProfile(name="Nubank", slug="nubank")
        rich = CompanyProfile(
            name="Nubank",
            slug="nubank",
            website="https://nubank.com",
            description="Digital bank",
            sector="Fintech",
            city="São Paulo",
        )
        result = dedup_profiles([sparse, rich])
        assert len(result) == 1
        assert result[0].website == "https://nubank.com"
        assert result[0].sector == "Fintech"

    def test_merges_tags(self):
        p1 = CompanyProfile(name="Nubank", slug="nubank", tags=["fintech", "neobank"])
        p2 = CompanyProfile(name="nubank", slug="nubank", tags=["ai", "fintech"])
        result = dedup_profiles([p1, p2])
        assert len(result) == 1
        assert sorted(result[0].tags) == ["ai", "fintech", "neobank"]

    def test_merges_tech_stack(self):
        p1 = CompanyProfile(name="Stone", slug="stone", tech_stack=["Go", "Python"])
        p2 = CompanyProfile(name="stone", slug="stone", tech_stack=["Python", "React"])
        result = dedup_profiles([p1, p2])
        assert len(result) == 1
        assert sorted(result[0].tech_stack) == ["Go", "Python", "React"]

    def test_fills_null_fields_from_donor(self):
        p1 = CompanyProfile(
            name="iFood", slug="ifood",
            website="https://ifood.com.br",
            description=None,
        )
        p2 = CompanyProfile(
            name="ifood", slug="ifood",
            description="Food delivery app",
            city="Osasco",
        )
        result = dedup_profiles([p1, p2])
        assert len(result) == 1
        assert result[0].website == "https://ifood.com.br"
        assert result[0].description == "Food delivery app"
        assert result[0].city == "Osasco"

    def test_three_duplicates_merged_to_one(self):
        profiles = [
            CompanyProfile(name="Azuki", slug="azuki", source_name="github_sao_paulo"),
            CompanyProfile(name="Azuki", slug="azuki", source_name="github_rio"),
            CompanyProfile(name="azuki", slug="Azuki", source_name="github_mexico_city"),
        ]
        result = dedup_profiles(profiles)
        assert len(result) == 1

    def test_dedup_uses_name_when_slug_is_none(self):
        p1 = CompanyProfile(name="Test Corp", slug=None, website="https://test.com")
        p2 = CompanyProfile(name="test corp", slug=None, description="A company")
        result = dedup_profiles([p1, p2])
        assert len(result) == 1
        assert result[0].website == "https://test.com"
        assert result[0].description == "A company"
