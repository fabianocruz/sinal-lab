"""Tests for YouTube and TikTok collectors (Monid-based)."""

from unittest.mock import MagicMock, patch

import pytest

from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.social_signals.collector import (
    collect_from_tiktok,
    collect_from_youtube,
    normalize_youtube_item,
)
from apps.agents.social_signals.models import SocialPost
from apps.agents.sources.monid import fetch_youtube_comments


class TestNormalizeYoutubeItem:
    def test_basic_normalization(self):
        item = {
            "videoTitle": "AI Agents in Fintech",
            "text": "Great video about AI",
            "videoUrl": "https://youtube.com/watch?v=123",
            "author": "TechChannel",
            "likes": 100,
            "viewCount": 5000,
            "commentCount": 50,
        }
        post = normalize_youtube_item(item)
        assert post.platform == "youtube"
        assert "AI Agents in Fintech" in post.text
        assert "Great video about AI" in post.text
        assert post.url == "https://youtube.com/watch?v=123"
        assert post.author_handle == "TechChannel"
        assert post.metrics["likes"] == 100
        assert post.metrics["views"] == 5000
        assert post.metrics["comments"] == 50
        assert post.source_name == "monid_youtube"

    def test_with_description_field(self):
        item = {
            "videoTitle": "Fintech LATAM",
            "description": "A long description about fintech in Latin America",
            "videoUrl": "https://youtube.com/watch?v=456",
        }
        post = normalize_youtube_item(item)
        assert "Fintech LATAM" in post.text
        assert "long description" in post.text

    def test_with_comment_field(self):
        item = {
            "comment": "This is interesting",
            "videoUrl": "https://youtube.com/watch?v=789",
        }
        post = normalize_youtube_item(item)
        assert "This is interesting" in post.text

    def test_with_channel_name(self):
        item = {
            "videoTitle": "Test",
            "url": "https://youtube.com/watch?v=abc",
            "channelName": "FinTech Weekly",
        }
        post = normalize_youtube_item(item)
        assert post.author_handle == "FinTech Weekly"

    def test_empty_item(self):
        item = {}
        post = normalize_youtube_item(item)
        assert post.text == ""
        assert post.url == ""
        assert post.platform == "youtube"

    def test_subscriber_count(self):
        item = {
            "videoTitle": "Test",
            "videoUrl": "https://youtube.com/watch?v=x",
            "subscriberCount": 10000,
        }
        post = normalize_youtube_item(item)
        assert post.author_followers == 10000

    def test_none_metrics_handled(self):
        """None values in metrics should default to 0."""
        item = {
            "videoTitle": "Test",
            "videoUrl": "https://youtube.com/watch?v=x",
            "likes": None,
            "viewCount": None,
            "commentCount": None,
            "subscriberCount": None,
        }
        post = normalize_youtube_item(item)
        assert post.metrics["likes"] == 0
        assert post.metrics["views"] == 0
        assert post.metrics["comments"] == 0
        assert post.author_followers == 0

    def test_fallback_url_field(self):
        item = {
            "videoTitle": "Test",
            "url": "https://youtube.com/watch?v=fallback",
        }
        post = normalize_youtube_item(item)
        assert post.url == "https://youtube.com/watch?v=fallback"


class TestFetchYoutubeComments:
    @patch("apps.agents.sources.monid.is_available", return_value=False)
    def test_not_available_returns_empty(self, mock_avail):
        result = fetch_youtube_comments("test query")
        assert result == []

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_returns_items(self, mock_avail, mock_run):
        mock_run.return_value = {
            "output": [
                {"videoUrl": "https://youtube.com/1", "videoTitle": "Test 1"},
                {"videoUrl": "https://youtube.com/2", "videoTitle": "Test 2"},
            ],
        }
        result = fetch_youtube_comments("AI fintech", max_results=10)
        assert len(result) == 2

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_empty_result(self, mock_avail, mock_run):
        mock_run.return_value = None
        result = fetch_youtube_comments("test")
        assert result == []

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_provenance_tracking(self, mock_avail, mock_run):
        mock_run.return_value = {
            "items": [{"videoUrl": "https://youtube.com/1"}],
        }
        prov = MagicMock()
        fetch_youtube_comments("test", provenance=prov)
        prov.track.assert_called_once()
        call_kwargs = prov.track.call_args[1]
        assert call_kwargs["source_name"] == "monid_youtube"


class TestCollectFromYoutube:
    @pytest.fixture(autouse=True)
    def _no_youtube_api_key(self, monkeypatch):
        """collect_from_youtube short-circuits to the real YouTube Data
        API when YOUTUBE_API_KEY is set; remove it so these tests
        exercise the Monid path they mock."""
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    @patch("apps.agents.sources.monid.is_available", return_value=False)
    def test_no_api_key_returns_empty(self, mock_avail):
        prov = ProvenanceTracker()
        result = collect_from_youtube(prov)
        assert result == []

    @patch("apps.agents.sources.monid.fetch_youtube_comments")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_collects_and_normalizes(self, mock_avail, mock_fetch):
        mock_fetch.return_value = [
            {"videoTitle": "AI in Banking", "videoUrl": "https://youtube.com/1", "likes": 50},
            {"videoTitle": "Fintech LATAM", "videoUrl": "https://youtube.com/2", "likes": 100},
        ]
        prov = ProvenanceTracker()
        result = collect_from_youtube(prov)
        assert len(result) == 4  # 2 default queries x 2 results each
        assert all(isinstance(p, SocialPost) for p in result)
        assert all(p.platform == "youtube" for p in result)

    @patch("apps.agents.sources.monid.fetch_youtube_comments")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_custom_queries(self, mock_avail, mock_fetch):
        mock_fetch.return_value = [
            {"videoTitle": "Custom", "videoUrl": "https://youtube.com/1"},
        ]
        prov = ProvenanceTracker()
        result = collect_from_youtube(prov, queries=["custom query"])
        assert len(result) == 1
        mock_fetch.assert_called_once_with("custom query", max_results=25, provenance=prov)

    @patch("apps.agents.sources.monid.fetch_youtube_comments")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_filters_empty_text_or_url(self, mock_avail, mock_fetch):
        mock_fetch.return_value = [
            {"videoTitle": "", "videoUrl": ""},  # Should be filtered
            {"videoTitle": "Valid", "videoUrl": "https://youtube.com/1"},
        ]
        prov = ProvenanceTracker()
        result = collect_from_youtube(prov, queries=["test"])
        assert len(result) == 1

    @patch("apps.agents.sources.monid.is_available", side_effect=Exception("network error"))
    def test_exception_returns_empty(self, mock_avail):
        prov = ProvenanceTracker()
        result = collect_from_youtube(prov)
        assert result == []


class TestCollectFromTiktok:
    @patch("apps.agents.sources.monid.is_available", return_value=False)
    def test_no_api_key_returns_empty(self, mock_avail):
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov)
        assert result == []

    @patch("apps.agents.sources.monid.discover", return_value=[])
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_no_endpoint_discovered(self, mock_avail, mock_discover):
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov)
        assert result == []

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.discover")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_discovered_endpoint_used(self, mock_avail, mock_discover, mock_run):
        mock_discover.return_value = [
            {"provider": "apify", "endpoint": "/tiktok/scraper"},
        ]
        mock_run.return_value = {
            "output": [
                {"text": "Fintech AI", "webVideoUrl": "https://tiktok.com/1"},
                {"description": "Banking tech", "url": "https://tiktok.com/2"},
            ],
        }
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov, queries=["test"])
        assert len(result) == 2
        assert all(p.platform == "tiktok" for p in result)

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.discover")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_filters_empty_posts(self, mock_avail, mock_discover, mock_run):
        mock_discover.return_value = [
            {"provider": "apify", "endpoint": "/tiktok/scraper"},
        ]
        mock_run.return_value = {
            "output": [
                {"text": "", "url": ""},  # Should be filtered
                {"text": "Valid post", "webVideoUrl": "https://tiktok.com/1"},
            ],
        }
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov, queries=["test"])
        assert len(result) == 1

    @patch("apps.agents.sources.monid.is_available", side_effect=Exception("fail"))
    def test_exception_returns_empty(self, mock_avail):
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov)
        assert result == []

    @patch("apps.agents.sources.monid.run_endpoint")
    @patch("apps.agents.sources.monid.discover")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_author_meta_dict(self, mock_avail, mock_discover, mock_run):
        mock_discover.return_value = [
            {"provider": "apify", "endpoint": "/tiktok/scraper"},
        ]
        mock_run.return_value = {
            "output": [
                {
                    "text": "Test",
                    "webVideoUrl": "https://tiktok.com/1",
                    "authorMeta": {"name": "user1", "nickName": "User One"},
                    "diggCount": 500,
                    "playCount": 10000,
                    "shareCount": 50,
                    "commentCount": 25,
                },
            ],
        }
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov, queries=["test"])
        assert len(result) == 1
        post = result[0]
        assert post.author_handle == "user1"
        assert post.author_display_name == "User One"
        assert post.metrics["likes"] == 500
        assert post.metrics["views"] == 10000

    @patch("apps.agents.sources.monid.discover")
    @patch("apps.agents.sources.monid.is_available", return_value=True)
    def test_endpoint_without_path(self, mock_avail, mock_discover):
        mock_discover.return_value = [
            {"provider": "apify", "endpoint": ""},  # Empty path
        ]
        prov = ProvenanceTracker()
        result = collect_from_tiktok(prov)
        assert result == []
