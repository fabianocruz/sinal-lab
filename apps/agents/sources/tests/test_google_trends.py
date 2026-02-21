"""Tests for shared Google Trends source module.

Tests GoogleTrendItem dataclass, fetch_trending_searches, and
fetch_related_queries functions. Uses mocked pytrends internals
to avoid real API calls.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.google_trends import (
    GoogleTrendItem,
    fetch_related_queries,
    fetch_trending_searches,
)


def _make_source(name: str = "google_trends_test") -> DataSourceConfig:
    """Helper to create a DataSourceConfig for Google Trends."""
    return DataSourceConfig(
        name=name,
        source_type="api",
        url="https://trends.google.com",
    )


class TestGoogleTrendItem:
    """Test GoogleTrendItem dataclass."""

    def test_auto_content_hash(self) -> None:
        """Hash computed from keyword+region+trend_type."""
        item = GoogleTrendItem(
            keyword="inteligencia artificial",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
        )
        assert item.content_hash
        assert len(item.content_hash) == 32  # MD5 hex digest

    def test_preserves_manual_hash(self) -> None:
        """Manual hash is not overwritten by __post_init__."""
        item = GoogleTrendItem(
            keyword="test",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
            content_hash="custom_hash_value",
        )
        assert item.content_hash == "custom_hash_value"

    def test_different_regions_different_hash(self) -> None:
        """Same keyword in different regions produces different hashes."""
        item_br = GoogleTrendItem(
            keyword="startup",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
        )
        item_mx = GoogleTrendItem(
            keyword="startup",
            source_name="trends",
            trend_type="trending_search",
            region="mexico",
        )
        assert item_br.content_hash != item_mx.content_hash

    def test_different_trend_types_different_hash(self) -> None:
        """Same keyword with different trend_type produces different hashes."""
        item_a = GoogleTrendItem(
            keyword="AI",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
        )
        item_b = GoogleTrendItem(
            keyword="AI",
            source_name="trends",
            trend_type="related_query",
            region="brazil",
        )
        assert item_a.content_hash != item_b.content_hash

    def test_same_inputs_same_hash(self) -> None:
        """Identical keyword+region+trend_type produces identical hashes."""
        item_a = GoogleTrendItem(
            keyword="fintech",
            source_name="source_a",
            trend_type="trending_search",
            region="brazil",
        )
        item_b = GoogleTrendItem(
            keyword="fintech",
            source_name="source_b",
            trend_type="trending_search",
            region="brazil",
        )
        assert item_a.content_hash == item_b.content_hash

    def test_auto_url_generation(self) -> None:
        """URL points to Google Trends explore page with encoded keyword."""
        item = GoogleTrendItem(
            keyword="machine learning",
            source_name="trends",
            trend_type="trending_search",
            region="BR",
        )
        assert "trends.google.com/trends/explore" in item.url
        assert "q=machine+learning" in item.url
        assert "geo=BR" in item.url

    def test_preserves_manual_url(self) -> None:
        """Manual URL is not overwritten by __post_init__."""
        item = GoogleTrendItem(
            keyword="test",
            source_name="trends",
            trend_type="trending_search",
            region="BR",
            url="https://custom.url/page",
        )
        assert item.url == "https://custom.url/page"

    def test_auto_collected_at(self) -> None:
        """collected_at is set to UTC now if not provided."""
        item = GoogleTrendItem(
            keyword="test",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
        )
        assert item.collected_at is not None
        assert item.collected_at.tzinfo == timezone.utc

    def test_preserves_manual_collected_at(self) -> None:
        """Manual collected_at is not overwritten."""
        manual_dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        item = GoogleTrendItem(
            keyword="test",
            source_name="trends",
            trend_type="trending_search",
            region="brazil",
            collected_at=manual_dt,
        )
        assert item.collected_at == manual_dt


class TestFetchTrendingSearches:
    """Test fetch_trending_searches via pytrends."""

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_success_returns_items(self, mock_trendreq_cls: MagicMock) -> None:
        """Mock pytrends.trending_searches() returning DataFrame."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        df = pd.DataFrame({0: ["inteligencia artificial", "startup brasil", "fintech"]})
        mock_pytrends.trending_searches.return_value = df

        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")

        assert len(items) == 3
        assert items[0].keyword == "inteligencia artificial"
        assert items[1].keyword == "startup brasil"
        assert items[2].keyword == "fintech"
        assert all(i.trend_type == "trending_search" for i in items)
        assert all(i.region == "brazil" for i in items)
        assert all(i.source_name == "google_trends_test" for i in items)
        mock_pytrends.trending_searches.assert_called_once_with(pn="brazil")

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_empty_results(self, mock_trendreq_cls: MagicMock) -> None:
        """Empty DataFrame returns empty list."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        df = pd.DataFrame({0: []})
        mock_pytrends.trending_searches.return_value = df

        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")
        assert items == []

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_network_error_returns_empty(self, mock_trendreq_cls: MagicMock) -> None:
        """Exception from pytrends returns [] (graceful degradation)."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends
        mock_pytrends.trending_searches.side_effect = Exception("Connection timeout")

        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")
        assert items == []

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_region_parameter(self, mock_trendreq_cls: MagicMock) -> None:
        """Region is passed to pytrends correctly."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        df = pd.DataFrame({0: ["test"]})
        mock_pytrends.trending_searches.return_value = df

        source = _make_source()
        fetch_trending_searches(source, region="mexico")

        mock_pytrends.trending_searches.assert_called_once_with(pn="mexico")

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_strips_whitespace_keywords(self, mock_trendreq_cls: MagicMock) -> None:
        """Leading/trailing whitespace in keywords is stripped."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        df = pd.DataFrame({0: ["  padded keyword  ", "  another  "]})
        mock_pytrends.trending_searches.return_value = df

        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")
        assert items[0].keyword == "padded keyword"
        assert items[1].keyword == "another"

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_skips_empty_keywords(self, mock_trendreq_cls: MagicMock) -> None:
        """Empty or whitespace-only keywords are skipped."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        df = pd.DataFrame({0: ["valid", "", "   ", "also valid"]})
        mock_pytrends.trending_searches.return_value = df

        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")
        assert len(items) == 2
        assert items[0].keyword == "valid"
        assert items[1].keyword == "also valid"

    @patch("apps.agents.sources.google_trends._pytrends_available", False)
    def test_pytrends_not_installed_returns_empty(self) -> None:
        """When pytrends is not available, returns empty list gracefully."""
        source = _make_source()
        items = fetch_trending_searches(source, region="brazil")
        assert items == []


class TestFetchRelatedQueries:
    """Test fetch_related_queries via pytrends."""

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_success_returns_rising_queries(self, mock_trendreq_cls: MagicMock) -> None:
        """Mock related_queries() with rising queries."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        rising_df = pd.DataFrame({
            "query": ["AI startup", "LLM tools"],
            "value": ["500%", "200%"],
        })
        top_df = pd.DataFrame({
            "query": ["machine learning", "deep learning"],
            "value": [100, 80],
        })

        mock_pytrends.related_queries.return_value = {
            "inteligencia artificial": {
                "rising": rising_df,
                "top": top_df,
            }
        }

        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["inteligencia artificial"], region="BR"
        )

        # Rising queries come first, then top queries
        rising_items = [i for i in items if i.trend_type == "related_query"]
        top_items = [i for i in items if i.trend_type == "rising_topic"]

        assert len(rising_items) == 2
        assert rising_items[0].keyword == "AI startup"
        assert rising_items[0].traffic_value == "500%"
        assert rising_items[0].region == "BR"
        assert "inteligencia artificial" in rising_items[0].related_queries

        assert len(top_items) == 2

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_empty_keywords_returns_empty(self, mock_trendreq_cls: MagicMock) -> None:
        """Empty keywords list returns empty list without calling API."""
        source = _make_source()
        items = fetch_related_queries(source, keywords=[], region="BR")
        assert items == []
        mock_trendreq_cls.assert_not_called()

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_network_error_returns_empty(self, mock_trendreq_cls: MagicMock) -> None:
        """Exception from pytrends returns [] (graceful degradation)."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends
        mock_pytrends.related_queries.side_effect = Exception("Rate limited")

        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["test"], region="BR"
        )
        assert items == []

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_multiple_keywords(self, mock_trendreq_cls: MagicMock) -> None:
        """Results from multiple keywords are combined."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        rising_ai = pd.DataFrame({
            "query": ["GPT-4", "Claude"],
            "value": ["300%", "250%"],
        })
        rising_fintech = pd.DataFrame({
            "query": ["Pix internacional", "Open Banking"],
            "value": ["400%", "150%"],
        })

        mock_pytrends.related_queries.return_value = {
            "AI": {
                "rising": rising_ai,
                "top": None,
            },
            "fintech": {
                "rising": rising_fintech,
                "top": None,
            },
        }

        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["AI", "fintech"], region="BR"
        )

        assert len(items) == 4
        keywords_found = {i.keyword for i in items}
        assert "GPT-4" in keywords_found
        assert "Claude" in keywords_found
        assert "Pix internacional" in keywords_found
        assert "Open Banking" in keywords_found

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_keywords_capped_at_five(self, mock_trendreq_cls: MagicMock) -> None:
        """pytrends only supports up to 5 keywords; extras are dropped."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends
        mock_pytrends.related_queries.return_value = {}

        source = _make_source()
        keywords = ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7"]
        fetch_related_queries(source, keywords=keywords, region="BR")

        call_args = mock_pytrends.build_payload.call_args
        actual_keywords = call_args[0][0]
        assert len(actual_keywords) == 5

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_none_data_for_keyword_skipped(self, mock_trendreq_cls: MagicMock) -> None:
        """Keywords returning None data are safely skipped."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        mock_pytrends.related_queries.return_value = {
            "obscure_term": None,
        }

        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["obscure_term"], region="BR"
        )
        assert items == []

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_timeframe_parameter(self, mock_trendreq_cls: MagicMock) -> None:
        """Timeframe is passed to pytrends build_payload correctly."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends
        mock_pytrends.related_queries.return_value = {}

        source = _make_source()
        fetch_related_queries(
            source,
            keywords=["test"],
            region="BR",
            timeframe="today 1-m",
        )

        call_args = mock_pytrends.build_payload.call_args
        assert call_args.kwargs.get("timeframe") == "today 1-m" or \
            call_args[1].get("timeframe") == "today 1-m"

    @patch("apps.agents.sources.google_trends._pytrends_available", False)
    def test_pytrends_not_installed_returns_empty(self) -> None:
        """When pytrends is not available, returns empty list gracefully."""
        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["test"], region="BR"
        )
        assert items == []

    @patch("apps.agents.sources.google_trends.TrendReq")
    def test_deduplicates_top_vs_rising(self, mock_trendreq_cls: MagicMock) -> None:
        """Top queries that already appear in rising are not duplicated."""
        mock_pytrends = MagicMock()
        mock_trendreq_cls.return_value = mock_pytrends

        rising_df = pd.DataFrame({
            "query": ["overlapping query"],
            "value": ["300%"],
        })
        top_df = pd.DataFrame({
            "query": ["overlapping query", "unique top query"],
            "value": [100, 80],
        })

        mock_pytrends.related_queries.return_value = {
            "seed": {
                "rising": rising_df,
                "top": top_df,
            }
        }

        source = _make_source()
        items = fetch_related_queries(
            source, keywords=["seed"], region="BR"
        )

        keyword_list = [i.keyword for i in items]
        assert keyword_list.count("overlapping query") == 1
        assert "unique top query" in keyword_list
