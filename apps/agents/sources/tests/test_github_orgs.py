"""Tests for shared GitHub org collection and enrichment."""

import pytest
from unittest.mock import Mock, patch

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.sources.github_orgs import (
    CompanyProfile,
    POSITIVE_SIGNALS,
    collect_from_github,
    enrich_from_github_org,
    enrich_github_profiles,
    is_likely_startup,
    score_startup_likelihood,
    _format_display_name,
    _resolve_location,
)


# --- Fixtures ---


@pytest.fixture
def github_source():
    return DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/users",
        enabled=True,
        params={"q": 'location:"São Paulo" type:org repos:>5', "sort": "repositories", "per_page": 30},
    )


@pytest.fixture
def provenance():
    return ProvenanceTracker()


@pytest.fixture
def mock_github_response():
    return {
        "total_count": 2,
        "items": [
            {
                "login": "nubank",
                "html_url": "https://github.com/nubank",
                "type": "Organization",
                "description": "Functional machine learning",
            },
            {
                "login": "stone-payments",
                "html_url": "https://github.com/stone-payments",
                "type": "Organization",
                "description": "Microservice gateway",
            },
        ],
    }


# --- is_likely_startup tests ---


class TestIsLikelyStartup:
    """Tests that blocklist filtering works correctly."""

    def test_real_startup_passes(self):
        assert is_likely_startup("nubank", "Functional machine learning")

    def test_filters_university(self):
        assert not is_likely_startup("FIAP", "")

    def test_filters_government(self):
        assert not is_likely_startup("prefeiturasp", "")

    def test_filters_exact_login_vtex(self):
        assert not is_likely_startup("vtex", "")

    def test_filters_archive(self):
        assert not is_likely_startup("alexfalcucci-archive", "")

    def test_allows_cloudwalk(self):
        assert is_likely_startup("cloudwalk-inc", "Payments infrastructure")


# --- score_startup_likelihood tests ---


class TestScoreStartupLikelihood:
    """Tests the numeric startup scoring."""

    def test_blocklisted_org_scores_zero(self):
        assert score_startup_likelihood("prefeiturasp", "Prefeitura de São Paulo") == 0.0

    def test_exact_login_blocklist_scores_zero(self):
        assert score_startup_likelihood("vtex", "") == 0.0

    def test_neutral_org_scores_base(self):
        """Org with no positive or negative signals gets 0.3."""
        score = score_startup_likelihood("some-random-co", "We build things")
        assert score == 0.3

    def test_startup_keywords_boost_score(self):
        """Org with 'fintech' and 'payments' keywords scores higher."""
        score = score_startup_likelihood("acme-pay", "fintech payments platform")
        assert score > 0.3
        assert score <= 1.0

    def test_multiple_keywords_increase_score(self):
        """More keyword hits = higher score."""
        score_low = score_startup_likelihood("acme", "cloud service")
        score_high = score_startup_likelihood("acme", "cloud saas fintech ai data analytics")
        assert score_high > score_low

    def test_score_capped_at_one(self):
        """Score never exceeds 1.0 even with many keywords."""
        text = " ".join(POSITIVE_SIGNALS)
        score = score_startup_likelihood("mega-co", text)
        assert score <= 1.0

    def test_bio_contributes_to_score(self):
        """Bio text is included in keyword matching."""
        score_no_bio = score_startup_likelihood("acme", "")
        score_with_bio = score_startup_likelihood("acme", "", bio="fintech startup")
        assert score_with_bio > score_no_bio

    def test_login_contributes_to_score(self):
        """Login text like 'fintech-co' can match positive signals."""
        score = score_startup_likelihood("fintech-co", "")
        assert score > 0.3


# --- _format_display_name tests ---


class TestFormatDisplayName:
    def test_hyphenated_login(self):
        assert _format_display_name("stone-payments") == "Stone Payments"

    def test_underscore_login(self):
        assert _format_display_name("cloud_walk") == "Cloud Walk"

    def test_single_word(self):
        assert _format_display_name("nubank") == "Nubank"


# --- _resolve_location tests ---


class TestResolveLocation:
    def test_sao_paulo(self):
        city, country = _resolve_location('location:"São Paulo" type:org')
        assert city == "São Paulo"
        assert country == "Brasil"

    def test_santiago(self):
        city, country = _resolve_location('location:"Santiago" type:org')
        assert city == "Santiago"
        assert country == "Chile"

    def test_lima(self):
        city, country = _resolve_location('location:"Lima" type:org')
        assert city == "Lima"
        assert country == "Peru"

    def test_unknown_location_defaults(self):
        city, country = _resolve_location('location:"Unknown" type:org')
        assert city is None
        assert country == "Brasil"


# --- collect_from_github tests ---


class TestCollectFromGithub:
    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_success(self, mock_get, mock_github_response, github_source, provenance):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_github_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        profiles = collect_from_github(github_source, provenance)

        assert len(profiles) == 2
        assert profiles[0].name == "Nubank"
        assert profiles[0].slug == "nubank"
        assert profiles[0].city == "São Paulo"
        assert profiles[0].country == "Brasil"

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_timeout(self, mock_get, github_source, provenance):
        import httpx
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        profiles = collect_from_github(github_source, provenance)
        assert profiles == []

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_http_error(self, mock_get, github_source, provenance):
        import httpx
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock()
        )
        mock_get.return_value = mock_response
        profiles = collect_from_github(github_source, provenance)
        assert profiles == []

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_filters_non_startups(self, mock_get, github_source, provenance):
        mock_response = Mock()
        mock_response.json.return_value = {
            "total_count": 3,
            "items": [
                {"login": "nubank", "html_url": "https://github.com/nubank", "description": "fintech platform"},
                {"login": "prefeiturasp", "html_url": "https://github.com/prefeiturasp", "description": "Prefeitura"},
                {"login": "stone-payments", "html_url": "https://github.com/stone-payments", "description": "payments"},
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        profiles = collect_from_github(github_source, provenance)
        assert len(profiles) == 2
        names = [p.name for p in profiles]
        assert "Nubank" in names
        assert "Stone Payments" in names

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_skips_empty_login(self, mock_get, github_source, provenance):
        mock_response = Mock()
        mock_response.json.return_value = {
            "total_count": 1,
            "items": [{"login": "", "html_url": "https://github.com/ghost"}],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        profiles = collect_from_github(github_source, provenance)
        assert profiles == []

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_custom_min_score_threshold(self, mock_get, github_source, provenance):
        """Higher min_startup_score filters out neutral orgs."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "total_count": 2,
            "items": [
                {"login": "acme-co", "html_url": "https://github.com/acme-co", "description": "We do stuff"},
                {"login": "fintech-pay", "html_url": "https://github.com/fintech-pay", "description": "fintech payments saas"},
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # With high threshold, only the fintech org should pass
        profiles = collect_from_github(github_source, provenance, min_startup_score=0.5)
        assert len(profiles) == 1
        assert profiles[0].slug == "fintech-pay"

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_santiago_location_resolved(self, mock_get, provenance):
        """Santiago source correctly resolves to Chile."""
        source = DataSourceConfig(
            name="github_santiago",
            source_type="api",
            url="https://api.github.com/search/users",
            params={"q": 'location:"Santiago" type:org repos:>3'},
        )
        mock_response = Mock()
        mock_response.json.return_value = {
            "total_count": 1,
            "items": [{"login": "latam-co", "html_url": "https://github.com/latam-co", "description": ""}],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        profiles = collect_from_github(source, provenance)
        assert profiles[0].city == "Santiago"
        assert profiles[0].country == "Chile"


# --- enrich_from_github_org tests ---


class TestEnrichFromGithubOrg:
    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_populates_fields(self, mock_get):
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

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_handles_404(self, mock_get):
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
        assert enriched.name == "Ghost"

    @patch("apps.agents.sources.github_orgs.httpx.get")
    def test_preserves_existing_website(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"blog": "https://other.com", "description": "", "public_repos": 5}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        profile = CompanyProfile(
            name="Existing",
            slug="existing",
            website="https://existing.com",
            github_url="https://github.com/existing",
            source_url="https://github.com/existing",
            source_name="github_sao_paulo",
        )

        enriched = enrich_from_github_org(profile)
        assert enriched.website == "https://existing.com"

    def test_skips_profile_without_github_url(self):
        profile = CompanyProfile(name="NoGithub", slug="nogithub", source_url="", source_name="test")
        enriched = enrich_from_github_org(profile)
        assert enriched.name == "NoGithub"

    def test_skips_profile_without_slug(self):
        profile = CompanyProfile(name="NoSlug", github_url="https://github.com/x", source_url="", source_name="test")
        enriched = enrich_from_github_org(profile)
        assert enriched.name == "NoSlug"


# --- enrich_github_profiles tests ---


class TestEnrichGithubProfiles:
    @patch("apps.agents.sources.github_orgs.enrich_from_github_org")
    def test_enriches_all_profiles(self, mock_enrich):
        mock_enrich.side_effect = lambda p: p  # passthrough
        profiles = [
            CompanyProfile(name="A", slug="a", source_url="", source_name="test"),
            CompanyProfile(name="B", slug="b", source_url="", source_name="test"),
        ]
        result = enrich_github_profiles(profiles, delay=0)
        assert len(result) == 2
        assert mock_enrich.call_count == 2

    @patch("apps.agents.sources.github_orgs.enrich_from_github_org")
    def test_handles_enrichment_error(self, mock_enrich):
        """If enrichment fails for one profile, original is kept."""
        mock_enrich.side_effect = [Exception("API error"), lambda p: p]
        profiles = [
            CompanyProfile(name="Fail", slug="fail", source_url="", source_name="test"),
        ]
        result = enrich_github_profiles(profiles, delay=0)
        assert len(result) == 1
        assert result[0].name == "Fail"
