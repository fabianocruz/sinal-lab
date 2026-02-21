"""Tests for shared Google News RSS source module.

Tests build_google_news_url, build_google_news_sources, and fetch_google_news
functions that wrap the shared RSS parser for Google News search feeds.
"""

import urllib.parse
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.google_news import (
    GOOGLE_NEWS_RSS_BASE,
    _CEID_MAP,
    build_google_news_sources,
    build_google_news_url,
    fetch_google_news,
)


class TestBuildGoogleNewsUrl:
    """Test URL building from query parameters."""

    def test_defaults(self) -> None:
        """Default language=pt-BR, country=BR, time_range=7d."""
        url = build_google_news_url("startup latam")
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "news.google.com"
        assert parsed.path == "/rss/search"
        assert params["hl"] == ["pt-BR"]
        assert params["gl"] == ["BR"]
        assert params["ceid"] == ["BR:pt-419"]
        assert params["q"] == ["startup latam when:7d"]

    def test_custom_language_and_country(self) -> None:
        """Custom language=en, country=MX."""
        url = build_google_news_url(
            "fintech mexico", language="en", country="MX"
        )
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        assert params["hl"] == ["en"]
        assert params["gl"] == ["MX"]
        assert params["ceid"] == ["MX:es-419"]
        assert params["q"] == ["fintech mexico when:7d"]

    def test_special_characters_encoded(self) -> None:
        """Query with accents/spaces properly URL-encoded."""
        url = build_google_news_url("inteligencia artificial Sao Paulo")
        # The URL should be valid and parseable
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        # urllib.parse.parse_qs decodes, so we check the raw value round-trips
        assert "inteligencia artificial Sao Paulo when:7d" in params["q"][0]

    def test_time_range_parameter(self) -> None:
        """when= parameter appended for time filtering."""
        url_1d = build_google_news_url("ai", time_range="1d")
        params_1d = urllib.parse.parse_qs(urllib.parse.urlparse(url_1d).query)
        assert params_1d["q"] == ["ai when:1d"]

        url_30d = build_google_news_url("ai", time_range="30d")
        params_30d = urllib.parse.parse_qs(urllib.parse.urlparse(url_30d).query)
        assert params_30d["q"] == ["ai when:30d"]

    def test_no_time_range(self) -> None:
        """time_range=None omits when: from query."""
        url = build_google_news_url("ai startups", time_range=None)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert params["q"] == ["ai startups"]
        assert "when:" not in params["q"][0]

    def test_ceid_fallback_for_unknown_country(self) -> None:
        """Unknown country code uses fallback ceid format."""
        url = build_google_news_url("tech", language="pt-BR", country="ZZ")
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert params["ceid"] == ["ZZ:pt"]

    def test_all_known_ceid_mappings(self) -> None:
        """Every country in _CEID_MAP produces the correct ceid."""
        for country, expected_ceid in _CEID_MAP.items():
            url = build_google_news_url("test", country=country)
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            assert params["ceid"] == [expected_ceid], (
                f"Country {country}: expected ceid={expected_ceid}, "
                f"got {params['ceid']}"
            )

    def test_url_starts_with_base(self) -> None:
        """All generated URLs start with the Google News RSS base."""
        url = build_google_news_url("anything")
        assert url.startswith(GOOGLE_NEWS_RSS_BASE)


class TestBuildGoogleNewsSources:
    """Test convenience function for building DataSourceConfig lists."""

    def test_builds_correct_configs(self) -> None:
        """Each query dict becomes a DataSourceConfig."""
        queries = [
            {"name": "latam_startups", "query": "startup latam"},
            {"name": "fintech_br", "query": "fintech brasil"},
        ]
        sources = build_google_news_sources(queries)

        assert len(sources) == 2
        assert all(isinstance(s, DataSourceConfig) for s in sources)
        assert sources[0].params["query"] == "startup latam"
        assert sources[1].params["query"] == "fintech brasil"

    def test_default_prefix(self) -> None:
        """Names use gnews_ prefix by default."""
        queries = [{"name": "test_query", "query": "test"}]
        sources = build_google_news_sources(queries)
        assert sources[0].name == "gnews_test_query"

    def test_custom_prefix(self) -> None:
        """Custom prefix used in names."""
        queries = [{"name": "test_query", "query": "test"}]
        sources = build_google_news_sources(queries, prefix="radar")
        assert sources[0].name == "radar_test_query"

    def test_default_params(self) -> None:
        """Default language, country, time_range populated in params."""
        queries = [{"name": "basic", "query": "startup"}]
        sources = build_google_news_sources(queries)
        params = sources[0].params

        assert params["language"] == "pt-BR"
        assert params["country"] == "BR"
        assert params["time_range"] == "7d"

    def test_custom_params_override_defaults(self) -> None:
        """Query-level overrides replace defaults."""
        queries = [
            {
                "name": "mx",
                "query": "startup mexico",
                "language": "es",
                "country": "MX",
                "time_range": "1d",
            }
        ]
        sources = build_google_news_sources(queries)
        params = sources[0].params

        assert params["language"] == "es"
        assert params["country"] == "MX"
        assert params["time_range"] == "1d"

    def test_source_type_is_rss(self) -> None:
        """All generated sources have source_type='rss'."""
        queries = [{"name": "test", "query": "test"}]
        sources = build_google_news_sources(queries)
        assert sources[0].source_type == "rss"

    def test_url_is_none(self) -> None:
        """URL is None (built at fetch time from params)."""
        queries = [{"name": "test", "query": "test"}]
        sources = build_google_news_sources(queries)
        assert sources[0].url is None

    def test_empty_queries_returns_empty(self) -> None:
        """Empty query list returns empty source list."""
        sources = build_google_news_sources([])
        assert sources == []


class TestFetchGoogleNews:
    """Test the fetch function that wraps fetch_rss_feed."""

    def _make_source(
        self,
        query: str = "startup latam",
        language: str = "pt-BR",
        country: str = "BR",
        time_range: str = "7d",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig with Google News params."""
        return DataSourceConfig(
            name="gnews_test",
            source_type="rss",
            url=None,
            max_items=max_items,
            params={
                "query": query,
                "language": language,
                "country": country,
                "time_range": time_range,
            },
        )

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_delegates_to_fetch_rss_feed(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Verifies URL is built from params and passed to fetch_rss_feed."""
        mock_fetch_rss.return_value = []
        source = self._make_source(query="ai startups")
        client = MagicMock(spec=httpx.Client)

        fetch_google_news(source, client)

        mock_fetch_rss.assert_called_once()
        call_args = mock_fetch_rss.call_args
        passed_source = call_args[0][0]
        passed_client = call_args[0][1]

        # The URL should have been built and set on the copied source
        assert passed_source.url is not None
        assert "ai+startups" in passed_source.url or "ai startups" in urllib.parse.unquote(passed_source.url)
        assert "news.google.com" in passed_source.url
        assert passed_client is client

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_does_not_mutate_original_source(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Original DataSourceConfig is not modified."""
        mock_fetch_rss.return_value = []
        source = self._make_source()
        original_url = source.url
        client = MagicMock(spec=httpx.Client)

        fetch_google_news(source, client)

        assert source.url == original_url  # Still None

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_missing_query_param_returns_empty(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Returns [] when source.params has no 'query' key."""
        source = DataSourceConfig(
            name="gnews_empty",
            source_type="rss",
            url=None,
            params={},
        )
        client = MagicMock(spec=httpx.Client)

        result = fetch_google_news(source, client)
        assert result == []
        mock_fetch_rss.assert_not_called()

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_empty_query_returns_empty(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Returns [] when query is an empty string."""
        source = DataSourceConfig(
            name="gnews_empty_str",
            source_type="rss",
            url=None,
            params={"query": ""},
        )
        client = MagicMock(spec=httpx.Client)

        result = fetch_google_news(source, client)
        assert result == []
        mock_fetch_rss.assert_not_called()

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_passes_max_items(self, mock_fetch_rss: MagicMock) -> None:
        """max_items from DataSourceConfig is respected."""
        mock_fetch_rss.return_value = []
        source = self._make_source(max_items=5)
        client = MagicMock(spec=httpx.Client)

        fetch_google_news(source, client)

        call_args = mock_fetch_rss.call_args
        passed_source = call_args[0][0]
        assert passed_source.max_items == 5

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_returns_rss_items(self, mock_fetch_rss: MagicMock) -> None:
        """Returns whatever fetch_rss_feed returns."""
        from apps.agents.sources.rss import RSSItem

        expected_items = [
            RSSItem(
                title="Test Article",
                url="https://example.com/1",
                source_name="gnews_test",
            ),
        ]
        mock_fetch_rss.return_value = expected_items
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_google_news(source, client)
        assert result == expected_items

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_url_contains_correct_params(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Built URL includes language, country, ceid from source params."""
        mock_fetch_rss.return_value = []
        source = self._make_source(
            query="fintech",
            language="es",
            country="MX",
            time_range="1d",
        )
        client = MagicMock(spec=httpx.Client)

        fetch_google_news(source, client)

        passed_source = mock_fetch_rss.call_args[0][0]
        parsed = urllib.parse.urlparse(passed_source.url)
        params = urllib.parse.parse_qs(parsed.query)

        assert params["hl"] == ["es"]
        assert params["gl"] == ["MX"]
        assert params["ceid"] == ["MX:es-419"]
        assert params["q"] == ["fintech when:1d"]

    @patch("apps.agents.sources.google_news.fetch_rss_feed")
    def test_preserves_source_name(
        self, mock_fetch_rss: MagicMock
    ) -> None:
        """Copied source keeps the original name."""
        mock_fetch_rss.return_value = []
        source = self._make_source()
        source.name = "gnews_custom_name"
        client = MagicMock(spec=httpx.Client)

        fetch_google_news(source, client)

        passed_source = mock_fetch_rss.call_args[0][0]
        assert passed_source.name == "gnews_custom_name"
