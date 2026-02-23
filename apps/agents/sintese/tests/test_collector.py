"""Tests for SINTESE collector module."""

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
        assert item.image_url is None
        assert item.video_url is None

    def test_video_url_stored_correctly(self):
        """video_url field is stored and accessible."""
        item = FeedItem(
            title="Video Article",
            url="https://example.com/article",
            source_name="test",
            video_url="https://youtube.com/watch?v=abc",
        )
        assert item.video_url == "https://youtube.com/watch?v=abc"

    def test_image_and_video_url_together(self):
        """Both image_url and video_url can be set simultaneously."""
        item = FeedItem(
            title="Rich Article",
            url="https://example.com/article",
            source_name="test",
            image_url="https://cdn.example.com/thumb.jpg",
            video_url="https://vimeo.com/123456",
        )
        assert item.image_url == "https://cdn.example.com/thumb.jpg"
        assert item.video_url == "https://vimeo.com/123456"

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


class TestFeedItemImageUrl:
    """Test image_url field on FeedItem dataclass."""

    def test_feeditem_has_image_url_when_provided(self):
        """FeedItem accepts and stores image_url."""
        item = FeedItem(
            title="Article with cover image",
            url="https://example.com/article",
            source_name="test_source",
            image_url="https://cdn.example.com/cover.jpg",
        )
        assert item.image_url == "https://cdn.example.com/cover.jpg"

    def test_feeditem_image_url_defaults_to_none(self):
        """image_url defaults to None when not provided."""
        item = FeedItem(
            title="Article without image",
            url="https://example.com/article",
            source_name="test_source",
        )
        assert item.image_url is None

    def test_feeditem_image_url_explicit_none(self):
        """image_url can be set explicitly to None."""
        item = FeedItem(
            title="Article",
            url="https://example.com/article",
            source_name="test_source",
            image_url=None,
        )
        assert item.image_url is None

    def test_rss_to_feed_passes_image_url(self):
        """_rss_to_feed maps image_url from RSSItem to FeedItem."""
        from apps.agents.sintese.collector import _rss_to_feed
        from apps.agents.sources.rss import RSSItem

        rss_item = RSSItem(
            title="RSS Article",
            url="https://example.com/rss-article",
            source_name="rss_source",
            image_url="https://cdn.example.com/thumbnail.png",
        )
        feed_item = _rss_to_feed(rss_item)

        assert feed_item.image_url == "https://cdn.example.com/thumbnail.png"

    def test_rss_to_feed_passes_none_image_url(self):
        """_rss_to_feed maps None image_url when RSSItem has no image."""
        from apps.agents.sintese.collector import _rss_to_feed
        from apps.agents.sources.rss import RSSItem

        rss_item = RSSItem(
            title="RSS Article No Image",
            url="https://example.com/no-image",
            source_name="rss_source",
        )
        feed_item = _rss_to_feed(rss_item)

        assert feed_item.image_url is None

    def test_rss_to_feed_preserves_all_fields_including_image(self):
        """_rss_to_feed faithfully copies all RSSItem fields including image_url."""
        from datetime import datetime, timezone
        from apps.agents.sintese.collector import _rss_to_feed
        from apps.agents.sources.rss import RSSItem

        published = datetime(2026, 2, 15, tzinfo=timezone.utc)
        rss_item = RSSItem(
            title="Full RSS Article",
            url="https://example.com/full",
            source_name="full_source",
            published_at=published,
            summary="Original summary text.",
            author="Jane Smith",
            tags=["fintech", "latam"],
            image_url="https://cdn.example.com/full-image.jpg",
        )
        feed_item = _rss_to_feed(rss_item)

        assert feed_item.title == rss_item.title
        assert feed_item.url == rss_item.url
        assert feed_item.source_name == rss_item.source_name
        assert feed_item.published_at == rss_item.published_at
        assert feed_item.summary == rss_item.summary
        assert feed_item.author == rss_item.author
        assert feed_item.tags == rss_item.tags
        assert feed_item.image_url == rss_item.image_url
