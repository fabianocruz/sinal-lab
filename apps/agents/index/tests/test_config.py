"""Tests for INDEX agent configuration.

Verifies data source completeness, parameter consistency, and that
every GitHub city source has a matching entry in _LOCATION_MAP.
"""

from apps.agents.index.config import INDEX_CONFIG, INDEX_SOURCES
from apps.agents.sources.github_orgs import _LOCATION_MAP


class TestIndexSources:
    """Verify the INDEX_SOURCES list is well-formed."""

    def test_at_least_30_github_sources(self):
        github = [s for s in INDEX_SOURCES if s.name.startswith("github_")]
        assert len(github) >= 30

    def test_all_github_sources_have_per_page_100(self):
        for s in INDEX_SOURCES:
            if s.name.startswith("github_"):
                assert s.params.get("per_page") == 100, f"{s.name} missing per_page=100"

    def test_all_github_sources_have_location_in_query(self):
        for s in INDEX_SOURCES:
            if s.name.startswith("github_"):
                q = s.params.get("q", "")
                assert "location:" in q, f"{s.name} missing location in query"
                assert "type:org" in q, f"{s.name} missing type:org in query"

    def test_every_github_city_resolvable_in_location_map(self):
        """Every GitHub source query must contain a city present in _LOCATION_MAP."""
        for s in INDEX_SOURCES:
            if not s.name.startswith("github_"):
                continue
            q = s.params.get("q", "")
            found = any(city in q for city in _LOCATION_MAP)
            assert found, f"{s.name} query '{q}' has no matching city in _LOCATION_MAP"

    def test_major_hubs_have_repos_gt_5(self):
        major = ["github_sao_paulo", "github_rio", "github_mexico_city", "github_buenos_aires"]
        for name in major:
            s = INDEX_CONFIG.get_source_by_name(name)
            assert s is not None, f"{name} not found in config"
            assert "repos:>5" in s.params.get("q", ""), f"{name} should use repos:>5"


class TestNonGithubSources:
    """Verify non-GitHub sources have correct caps."""

    def test_abstartups_max_pages(self):
        s = INDEX_CONFIG.get_source_by_name("abstartups")
        assert s is not None
        assert s.params.get("max_pages") == 100

    def test_coresignal_max_collect(self):
        s = INDEX_CONFIG.get_source_by_name("coresignal_latam")
        assert s is not None
        assert s.params.get("max_collect") == 2000

    def test_crunchbase_api_enabled(self):
        s = INDEX_CONFIG.get_source_by_name("crunchbase_companies_latam")
        assert s is not None
        assert s.enabled is True
        assert s.params.get("limit") == 500

    def test_crunchbase_api_has_locations(self):
        s = INDEX_CONFIG.get_source_by_name("crunchbase_companies_latam")
        locations = s.params.get("locations", "")
        assert "Brazil" in locations
        assert "Mexico" in locations
        assert "Argentina" in locations

    def test_all_expected_sources_present(self):
        names = {s.name for s in INDEX_SOURCES}
        expected = {
            "abstartups", "yc_portfolio", "startups_latam",
            "coresignal_latam", "crunchbase_companies_latam",
        }
        assert expected.issubset(names)
