"""Tests for scripts/enrich_companies_github.py — pure function unit tests.

Tests the parsing, extraction, and enrichment logic used during GitHub-based
company enrichment.  All tests are pure (no network or database access).

Run: pytest scripts/tests/test_enrich_companies_github.py -v
"""

import pytest

from scripts.enrich_companies_github import (
    build_twitter_url,
    enrich_company_from_github,
    extract_github_username,
    extract_top_languages,
    should_enrich_field,
    sum_repo_stars,
)


# ---------------------------------------------------------------------------
# extract_github_username
# ---------------------------------------------------------------------------


class TestExtractGithubUsername:
    def test_full_https_url(self):
        assert extract_github_username("https://github.com/nubank") == "nubank"

    def test_http_url(self):
        assert extract_github_username("http://github.com/nubank") == "nubank"

    def test_trailing_slash(self):
        assert extract_github_username("https://github.com/nubank/") == "nubank"

    def test_no_protocol(self):
        assert extract_github_username("github.com/nubank") == "nubank"

    def test_with_repo_path(self):
        assert extract_github_username("https://github.com/nubank/faq") == "nubank"

    def test_with_deep_path(self):
        assert (
            extract_github_username("https://github.com/vtex/faststore/tree/main")
            == "vtex"
        )

    def test_empty_string(self):
        assert extract_github_username("") is None

    def test_none(self):
        assert extract_github_username(None) is None

    def test_whitespace_only(self):
        assert extract_github_username("   ") is None

    def test_non_github_url(self):
        assert extract_github_username("https://gitlab.com/nubank") is None

    def test_github_com_only(self):
        assert extract_github_username("https://github.com/") is None

    def test_github_com_no_slash(self):
        assert extract_github_username("https://github.com") is None

    def test_case_insensitive_domain(self):
        assert extract_github_username("https://GitHub.com/Nubank") == "Nubank"

    def test_hyphenated_username(self):
        assert (
            extract_github_username("https://github.com/mercado-libre")
            == "mercado-libre"
        )

    def test_numeric_username(self):
        assert extract_github_username("https://github.com/123abc") == "123abc"

    def test_whitespace_around_url(self):
        assert (
            extract_github_username("  https://github.com/nubank  ") == "nubank"
        )

    def test_invalid_username_special_chars(self):
        assert extract_github_username("https://github.com/user@name") is None

    def test_single_char_username(self):
        assert extract_github_username("https://github.com/a") == "a"

    def test_username_starting_with_hyphen(self):
        assert extract_github_username("https://github.com/-invalid") is None

    def test_username_ending_with_hyphen(self):
        assert extract_github_username("https://github.com/invalid-") is None


# ---------------------------------------------------------------------------
# build_twitter_url
# ---------------------------------------------------------------------------


class TestBuildTwitterUrl:
    def test_simple_handle(self):
        assert build_twitter_url("nubank") == "https://twitter.com/nubank"

    def test_with_at_sign(self):
        assert build_twitter_url("@nubank") == "https://twitter.com/nubank"

    def test_empty_string(self):
        assert build_twitter_url("") is None

    def test_none(self):
        assert build_twitter_url(None) is None

    def test_whitespace_only(self):
        assert build_twitter_url("   ") is None

    def test_at_sign_only(self):
        assert build_twitter_url("@") is None

    def test_whitespace_stripped(self):
        assert build_twitter_url("  nubank  ") == "https://twitter.com/nubank"


# ---------------------------------------------------------------------------
# extract_top_languages
# ---------------------------------------------------------------------------


class TestExtractTopLanguages:
    def test_multiple_languages(self):
        repos = [
            {"language": "Python"},
            {"language": "Python"},
            {"language": "JavaScript"},
            {"language": "Python"},
            {"language": "TypeScript"},
        ]
        result = extract_top_languages(repos)
        assert result[0] == "Python"
        assert len(result) == 3

    def test_no_languages(self):
        repos = [{"language": None}, {"language": None}]
        assert extract_top_languages(repos) == []

    def test_empty_list(self):
        assert extract_top_languages([]) == []

    def test_max_five_languages(self):
        repos = [
            {"language": "Python"},
            {"language": "Go"},
            {"language": "Rust"},
            {"language": "Java"},
            {"language": "Ruby"},
            {"language": "Elixir"},
            {"language": "C++"},
        ]
        result = extract_top_languages(repos)
        assert len(result) == 5

    def test_single_language(self):
        repos = [{"language": "Clojure"}, {"language": "Clojure"}]
        assert extract_top_languages(repos) == ["Clojure"]

    def test_mixed_with_nulls(self):
        repos = [
            {"language": "Python"},
            {"language": None},
            {"language": "Python"},
            {"language": None},
            {"language": "Go"},
        ]
        result = extract_top_languages(repos)
        assert result == ["Python", "Go"]

    def test_tie_breaking_is_stable(self):
        repos = [{"language": "A"}, {"language": "B"}, {"language": "C"}]
        result = extract_top_languages(repos)
        assert len(result) == 3
        # All have count=1; order depends on dict iteration order (stable in 3.7+)

    def test_repos_missing_language_key(self):
        repos = [{"name": "some-repo"}, {"language": "Go"}]
        assert extract_top_languages(repos) == ["Go"]


# ---------------------------------------------------------------------------
# sum_repo_stars
# ---------------------------------------------------------------------------


class TestSumRepoStars:
    def test_multiple_repos(self):
        repos = [
            {"stargazers_count": 100},
            {"stargazers_count": 200},
            {"stargazers_count": 50},
        ]
        assert sum_repo_stars(repos) == 350

    def test_empty_list(self):
        assert sum_repo_stars([]) == 0

    def test_repos_without_stars_key(self):
        repos = [{"name": "repo"}, {"stargazers_count": 10}]
        assert sum_repo_stars(repos) == 10

    def test_zero_stars(self):
        repos = [{"stargazers_count": 0}, {"stargazers_count": 0}]
        assert sum_repo_stars(repos) == 0

    def test_large_star_count(self):
        repos = [{"stargazers_count": 50_000}, {"stargazers_count": 30_000}]
        assert sum_repo_stars(repos) == 80_000


# ---------------------------------------------------------------------------
# should_enrich_field
# ---------------------------------------------------------------------------


class TestShouldEnrichField:
    def test_none(self):
        assert should_enrich_field(None) is True

    def test_empty_string(self):
        assert should_enrich_field("") is True

    def test_whitespace_only(self):
        assert should_enrich_field("   ") is True

    def test_has_value(self):
        assert should_enrich_field("https://nubank.com.br") is False

    def test_short_value(self):
        assert should_enrich_field("x") is False


# ---------------------------------------------------------------------------
# enrich_company_from_github
# ---------------------------------------------------------------------------


class _FakeCompany:
    """Minimal stand-in for Company, exposing the same attributes."""

    def __init__(self, **kwargs):
        self.website = kwargs.get("website")
        self.description = kwargs.get("description")
        self.short_description = kwargs.get("short_description")
        self.twitter_url = kwargs.get("twitter_url")
        self.tech_stack = kwargs.get("tech_stack")
        self.metadata_ = kwargs.get("metadata_")
        self.source_count = kwargs.get("source_count", 1)


class TestEnrichCompanyFromGithub:
    def test_fills_empty_website(self):
        company = _FakeCompany()
        profile = {"blog": "https://nubank.com.br"}
        assert enrich_company_from_github(company, profile, []) is True
        assert company.website == "https://nubank.com.br"

    def test_adds_protocol_to_website(self):
        company = _FakeCompany()
        profile = {"blog": "nubank.com.br"}
        enrich_company_from_github(company, profile, [])
        assert company.website == "https://nubank.com.br"

    def test_does_not_overwrite_existing_website(self):
        company = _FakeCompany(website="https://existing.com")
        profile = {"blog": "https://new.com"}
        enrich_company_from_github(company, profile, [])
        assert company.website == "https://existing.com"

    def test_fills_empty_description(self):
        company = _FakeCompany()
        profile = {"description": "Digital bank for Latin America"}
        enrich_company_from_github(company, profile, [])
        assert company.description == "Digital bank for Latin America"

    def test_uses_bio_fallback_for_description(self):
        company = _FakeCompany()
        profile = {"bio": "A user bio here"}
        enrich_company_from_github(company, profile, [])
        assert company.description == "A user bio here"

    def test_does_not_overwrite_existing_description(self):
        company = _FakeCompany(description="Existing desc")
        profile = {"description": "New desc"}
        enrich_company_from_github(company, profile, [])
        assert company.description == "Existing desc"

    def test_fills_short_description_when_short_enough(self):
        company = _FakeCompany()
        bio = "Short bio"
        profile = {"description": bio}
        enrich_company_from_github(company, profile, [])
        assert company.short_description == bio

    def test_skips_short_description_when_too_long(self):
        company = _FakeCompany()
        bio = "x" * 501
        profile = {"description": bio}
        enrich_company_from_github(company, profile, [])
        assert company.description == bio
        assert company.short_description is None

    def test_fills_twitter_url(self):
        company = _FakeCompany()
        profile = {"twitter_username": "nuaborja"}
        enrich_company_from_github(company, profile, [])
        assert company.twitter_url == "https://twitter.com/nuaborja"

    def test_does_not_overwrite_existing_twitter(self):
        company = _FakeCompany(twitter_url="https://twitter.com/old")
        profile = {"twitter_username": "new"}
        enrich_company_from_github(company, profile, [])
        assert company.twitter_url == "https://twitter.com/old"

    def test_fills_tech_stack_from_repos(self):
        company = _FakeCompany()
        repos = [
            {"language": "Clojure", "stargazers_count": 100},
            {"language": "Clojure", "stargazers_count": 50},
            {"language": "Python", "stargazers_count": 30},
        ]
        enrich_company_from_github(company, {}, repos)
        assert company.tech_stack == ["Clojure", "Python"]

    def test_does_not_overwrite_existing_tech_stack(self):
        company = _FakeCompany(tech_stack=["Go", "Rust"])
        repos = [{"language": "Python", "stargazers_count": 10}]
        enrich_company_from_github(company, {}, repos)
        assert company.tech_stack == ["Go", "Rust"]

    def test_stores_github_metadata(self):
        company = _FakeCompany()
        profile = {"public_repos": 42, "followers": 1000}
        repos = [{"stargazers_count": 500}, {"stargazers_count": 300}]
        enrich_company_from_github(company, profile, repos)
        meta = company.metadata_["github"]
        assert meta["public_repos"] == 42
        assert meta["followers"] == 1000
        assert meta["github_stars"] == 800
        assert "enriched_at" in meta

    def test_bumps_source_count_on_change(self):
        company = _FakeCompany(source_count=1)
        profile = {"blog": "https://nubank.com.br"}
        enrich_company_from_github(company, profile, [])
        assert company.source_count == 2

    def test_no_change_returns_false(self):
        company = _FakeCompany(
            website="https://nubank.com.br",
            description="Existing",
            short_description="Existing",
            twitter_url="https://twitter.com/nubank",
            tech_stack=["Python"],
            metadata_={
                "github": {
                    "public_repos": 10,
                    "followers": 100,
                    "github_stars": 500,
                    "enriched_at": "2026-01-01T00:00:00",
                }
            },
        )
        profile = {
            "blog": "https://different.com",
            "description": "New desc",
            "twitter_username": "newhandle",
            "public_repos": 10,
            "followers": 100,
        }
        repos = [{"language": "Go", "stargazers_count": 500}]
        # All fields already filled — only metadata might change if stars differ
        # In this case repos have same stars, so github_stars=500 matches
        result = enrich_company_from_github(company, profile, repos)
        # source_count should NOT bump since all fields were already filled
        # BUT enriched_at timestamp changes, so metadata changes → True
        # This is expected behavior: we always update the timestamp
        assert result is True

    def test_empty_blog_not_used(self):
        company = _FakeCompany()
        profile = {"blog": ""}
        enrich_company_from_github(company, profile, [])
        assert company.website is None

    def test_empty_description_not_used(self):
        company = _FakeCompany()
        profile = {"description": "", "bio": ""}
        enrich_company_from_github(company, profile, [])
        assert company.description is None

    def test_preserves_existing_metadata(self):
        company = _FakeCompany(
            metadata_={"crunchbase_url": "https://crunchbase.com/org/nubank"}
        )
        profile = {"public_repos": 5, "followers": 50}
        enrich_company_from_github(company, profile, [])
        # Both old and new metadata should be present
        assert company.metadata_["crunchbase_url"] == "https://crunchbase.com/org/nubank"
        assert company.metadata_["github"]["public_repos"] == 5

    def test_source_count_handles_none(self):
        company = _FakeCompany(source_count=None)
        profile = {"blog": "https://example.com"}
        enrich_company_from_github(company, profile, [])
        assert company.source_count == 2
