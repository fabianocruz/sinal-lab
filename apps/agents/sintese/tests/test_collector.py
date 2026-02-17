"""Tests for SINTESE collector module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone

from apps.agents.sintese.collector import (
    FeedItem,
    parse_feed_entry,
    extract_tags,
)


class TestFeedItem:
    """Test FeedItem dataclass."""

    def test_create_feed_item(self):
        item = FeedItem(
            title="Test Article",
            url="https://example.com/article",
            source_name="example",
        )
        assert item.title == "Test Article"
        assert item.url == "https://example.com/article"
        assert item.content_hash != ""

    def test_content_hash_from_url(self):
        item1 = FeedItem(title="A", url="https://example.com/1", source_name="s")
        item2 = FeedItem(title="B", url="https://example.com/1", source_name="s")
        item3 = FeedItem(title="A", url="https://example.com/2", source_name="s")

        # Same URL -> same hash (deduplication)
        assert item1.content_hash == item2.content_hash
        # Different URL -> different hash
        assert item1.content_hash != item3.content_hash

    def test_default_values(self):
        item = FeedItem(title="T", url="https://x.com", source_name="s")
        assert item.published_at is None
        assert item.summary is None
        assert item.author is None
        assert item.tags == []

    def test_full_item(self):
        now = datetime.now(timezone.utc)
        item = FeedItem(
            title="Nubank raises Series G",
            url="https://techcrunch.com/nubank",
            source_name="techcrunch",
            published_at=now,
            summary="Nubank raised $750M in Series G...",
            author="John Doe",
            tags=["fintech", "brazil", "funding"],
        )
        assert item.author == "John Doe"
        assert len(item.tags) == 3


class TestParseFeedEntry:
    """Test feed entry parsing."""

    def test_parse_minimal_entry(self):
        class MockEntry:
            title = "Test Title"
            link = "https://example.com"

        item = parse_feed_entry(MockEntry(), "test_source")
        assert item is not None
        assert item.title == "Test Title"
        assert item.url == "https://example.com"
        assert item.source_name == "test_source"

    def test_parse_entry_no_title(self):
        class MockEntry:
            title = None
            link = "https://example.com"

        item = parse_feed_entry(MockEntry(), "test")
        assert item is None

    def test_parse_entry_no_link(self):
        class MockEntry:
            title = "Test"
            link = None

        item = parse_feed_entry(MockEntry(), "test")
        assert item is None

    def test_parse_entry_with_summary(self):
        class MockEntry:
            title = "Test"
            link = "https://example.com"
            summary = "This is a summary"
            author = "Author Name"

        item = parse_feed_entry(MockEntry(), "test")
        assert item is not None
        assert item.summary == "This is a summary"
        assert item.author == "Author Name"

    def test_parse_entry_truncates_long_summary(self):
        class MockEntry:
            title = "Test"
            link = "https://example.com"
            summary = "x" * 2000

        item = parse_feed_entry(MockEntry(), "test")
        assert item is not None
        assert len(item.summary) <= 1003  # 1000 + "..."

    def test_parse_entry_strips_whitespace(self):
        class MockEntry:
            title = "  Test Title  "
            link = "  https://example.com  "

        item = parse_feed_entry(MockEntry(), "test")
        assert item is not None
        assert item.title == "Test Title"
        assert item.url == "https://example.com"


class TestExtractTags:
    """Test tag extraction from feed entries."""

    def test_extract_dict_tags(self):
        class MockEntry:
            tags = [{"term": "Python"}, {"term": "AI"}, {"term": "Startups"}]

        tags = extract_tags(MockEntry())
        assert len(tags) == 3
        assert "python" in tags
        assert "ai" in tags

    def test_extract_empty_tags(self):
        class MockEntry:
            tags = []

        tags = extract_tags(MockEntry())
        assert tags == []

    def test_no_tags_attribute(self):
        class MockEntry:
            pass

        tags = extract_tags(MockEntry())
        assert tags == []

    def test_tags_capped_at_10(self):
        class MockEntry:
            tags = [{"term": f"tag{i}"} for i in range(20)]

        tags = extract_tags(MockEntry())
        assert len(tags) == 10


class TestMultiSourceRouting:
    """Test multi-source routing in collect_all_sources."""

    def test_collect_all_sources_exists(self):
        """collect_all_sources should be importable."""
        from apps.agents.sintese.collector import collect_all_sources
        assert callable(collect_all_sources)

    def test_backward_compatible_alias(self):
        """collect_all_feeds should still be importable (backward compat)."""
        from apps.agents.sintese.collector import collect_all_feeds
        assert callable(collect_all_feeds)

    def test_collect_all_sources_routes_twitter(self):
        """Twitter sources should be routed to twitter_collector."""
        from unittest.mock import patch, MagicMock
        from apps.agents.sintese.collector import collect_all_sources
        from apps.agents.base.config import DataSourceConfig
        from apps.agents.base.provenance import ProvenanceTracker

        sources = [
            DataSourceConfig(
                name="twitter_fintech", source_type="api",
                api_key_env="X_BEARER_TOKEN",
                params={"territory": "fintech"},
            ),
        ]
        provenance = ProvenanceTracker()

        with patch("apps.agents.sintese.twitter_collector.collect_twitter_sources") as mock_twitter:
            mock_twitter.return_value = [
                FeedItem(title="Tweet item", url="https://x.com/1", source_name="twitter_fintech"),
            ]
            items = collect_all_sources(sources, provenance)

        mock_twitter.assert_called_once()
        assert len(items) >= 1

    def test_collect_all_sources_routes_rss(self):
        """RSS sources should still go through fetch_feed."""
        from unittest.mock import patch, MagicMock
        from apps.agents.sintese.collector import collect_all_sources
        from apps.agents.base.config import DataSourceConfig
        from apps.agents.base.provenance import ProvenanceTracker

        sources = [
            DataSourceConfig(name="test_rss", source_type="rss", url="https://example.com/feed"),
        ]
        provenance = ProvenanceTracker()

        with patch("apps.agents.sintese.collector.fetch_feed") as mock_fetch:
            mock_fetch.return_value = [
                FeedItem(title="RSS item", url="https://example.com/1", source_name="test_rss"),
            ]
            items = collect_all_sources(sources, provenance)

        mock_fetch.assert_called_once()
        assert len(items) == 1

    def test_collect_all_sources_deduplicates_across_types(self):
        """Same URL from RSS + Twitter should be kept only once."""
        from unittest.mock import patch, MagicMock
        from apps.agents.sintese.collector import collect_all_sources
        from apps.agents.base.config import DataSourceConfig
        from apps.agents.base.provenance import ProvenanceTracker

        shared_url = "https://techcrunch.com/shared-article"
        sources = [
            DataSourceConfig(name="test_rss", source_type="rss", url="https://example.com/feed"),
            DataSourceConfig(
                name="twitter_fintech", source_type="api",
                api_key_env="X_BEARER_TOKEN",
                params={"territory": "fintech"},
            ),
        ]
        provenance = ProvenanceTracker()

        with patch("apps.agents.sintese.collector.fetch_feed") as mock_rss, \
             patch("apps.agents.sintese.twitter_collector.collect_twitter_sources") as mock_twitter:
            mock_rss.return_value = [
                FeedItem(title="Article", url=shared_url, source_name="test_rss"),
            ]
            mock_twitter.return_value = [
                FeedItem(title="Tweet about article", url=shared_url, source_name="twitter_fintech"),
            ]
            items = collect_all_sources(sources, provenance)

        # Same URL → only 1 item after dedup
        assert len(items) == 1
