"""Tests for YouTube Data API v3 source module.

Tests YouTubeVideo dataclass, fetch_youtube_videos function,
thumbnail selection, URL computation, and graceful degradation
when credentials are missing.
"""

import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.sources.youtube import (
    YOUTUBE_SEARCH_URL,
    YOUTUBE_VIDEOS_URL,
    YouTubeVideo,
    _parse_search_results,
    _select_best_thumbnail,
    fetch_youtube_videos,
)


# ---------------------------------------------------------------------------
# Sample mock responses
# ---------------------------------------------------------------------------

SAMPLE_SEARCH_RESPONSE = {
    "items": [
        {
            "id": {"kind": "youtube#video", "videoId": "abc123"},
            "snippet": {
                "title": "AI Agents para Fintech na America Latina",
                "description": "Como AI agents estao transformando o setor financeiro na LATAM.",
                "channelId": "UCchannel1",
                "channelTitle": "Tech LATAM",
                "publishedAt": "2026-03-10T14:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/abc123/default.jpg", "width": 120, "height": 90},
                    "medium": {"url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg", "width": 320, "height": 180},
                    "high": {"url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg", "width": 480, "height": 360},
                },
            },
        },
        {
            "id": {"kind": "youtube#video", "videoId": "def456"},
            "snippet": {
                "title": "Open Banking Brasil: O que muda em 2026",
                "description": "Analise completa do open banking no Brasil.",
                "channelId": "UCchannel2",
                "channelTitle": "Fintech BR",
                "publishedAt": "2026-03-09T10:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/def456/default.jpg", "width": 120, "height": 90},
                },
            },
        },
    ],
}

SAMPLE_VIDEOS_RESPONSE = {
    "items": [
        {
            "id": "abc123",
            "statistics": {
                "viewCount": "150000",
                "likeCount": "4500",
                "commentCount": "320",
            },
            "contentDetails": {
                "duration": "PT15M32S",
            },
        },
        {
            "id": "def456",
            "statistics": {
                "viewCount": "25000",
                "likeCount": "800",
                "commentCount": "45",
            },
            "contentDetails": {
                "duration": "PT8M10S",
            },
        },
    ],
}


class TestYouTubeVideo:
    """Test YouTubeVideo dataclass, URL computation, and content hash."""

    def test_url_computed_from_video_id(self) -> None:
        """url is computed from video_id when not provided."""
        video = YouTubeVideo(
            video_id="abc123",
            title="Test",
            description="",
            channel_id="UCtest",
            channel_title="Test Channel",
        )
        assert video.url == "https://www.youtube.com/watch?v=abc123"

    def test_embed_url_computed_from_video_id(self) -> None:
        """embed_url is computed from video_id when not provided."""
        video = YouTubeVideo(
            video_id="abc123",
            title="Test",
            description="",
            channel_id="UCtest",
            channel_title="Test Channel",
        )
        assert video.embed_url == "https://www.youtube.com/embed/abc123"

    def test_content_hash_computed_from_url(self) -> None:
        """content_hash is computed as MD5 of the video URL."""
        video = YouTubeVideo(
            video_id="abc123",
            title="Test",
            description="",
            channel_id="UCtest",
            channel_title="Test Channel",
        )
        expected_url = "https://www.youtube.com/watch?v=abc123"
        expected_hash = hashlib.md5(expected_url.encode()).hexdigest()
        assert video.content_hash == expected_hash

    def test_custom_url_not_overwritten(self) -> None:
        """Custom url is preserved, not overwritten by computed value."""
        custom_url = "https://youtu.be/custom"
        video = YouTubeVideo(
            video_id="abc123",
            title="Test",
            description="",
            channel_id="UCtest",
            channel_title="Test Channel",
            url=custom_url,
        )
        assert video.url == custom_url

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Custom content_hash is preserved."""
        custom_hash = "custom_hash_12345"
        video = YouTubeVideo(
            video_id="abc123",
            title="Test",
            description="",
            channel_id="UCtest",
            channel_title="Test Channel",
            content_hash=custom_hash,
        )
        assert video.content_hash == custom_hash

    def test_default_values(self) -> None:
        """Default values set correctly (counts=0, optionals=None)."""
        video = YouTubeVideo(
            video_id="abc123",
            title="Minimal",
            description="",
            channel_id="UCtest",
            channel_title="Test",
        )
        assert video.published_at is None
        assert video.thumbnail_url is None
        assert video.view_count == 0
        assert video.like_count == 0
        assert video.comment_count == 0
        assert video.subscriber_count == 0
        assert video.duration == ""

    def test_all_fields_populated(self) -> None:
        """All fields populated correctly."""
        published = datetime(2026, 3, 10, 14, 0, 0, tzinfo=timezone.utc)
        video = YouTubeVideo(
            video_id="abc123",
            title="Full video",
            description="Description text",
            channel_id="UCchannel1",
            channel_title="Tech LATAM",
            published_at=published,
            thumbnail_url="https://i.ytimg.com/vi/abc123/hqdefault.jpg",
            view_count=150000,
            like_count=4500,
            comment_count=320,
            subscriber_count=50000,
            duration="PT15M32S",
        )
        assert video.title == "Full video"
        assert video.description == "Description text"
        assert video.channel_id == "UCchannel1"
        assert video.channel_title == "Tech LATAM"
        assert video.published_at == published
        assert video.view_count == 150000
        assert video.like_count == 4500
        assert video.comment_count == 320
        assert video.subscriber_count == 50000
        assert video.duration == "PT15M32S"
        assert video.content_hash != ""


class TestSelectBestThumbnail:
    """Test thumbnail quality selection logic."""

    def test_prefers_maxres(self) -> None:
        """Selects maxres when available."""
        thumbnails = {
            "default": {"url": "https://img/default.jpg"},
            "medium": {"url": "https://img/medium.jpg"},
            "high": {"url": "https://img/high.jpg"},
            "maxres": {"url": "https://img/maxres.jpg"},
        }
        assert _select_best_thumbnail(thumbnails) == "https://img/maxres.jpg"

    def test_falls_back_to_high(self) -> None:
        """Falls back to high when maxres is not available."""
        thumbnails = {
            "default": {"url": "https://img/default.jpg"},
            "medium": {"url": "https://img/medium.jpg"},
            "high": {"url": "https://img/high.jpg"},
        }
        assert _select_best_thumbnail(thumbnails) == "https://img/high.jpg"

    def test_falls_back_to_medium(self) -> None:
        """Falls back to medium when high and maxres are not available."""
        thumbnails = {
            "default": {"url": "https://img/default.jpg"},
            "medium": {"url": "https://img/medium.jpg"},
        }
        assert _select_best_thumbnail(thumbnails) == "https://img/medium.jpg"

    def test_falls_back_to_default(self) -> None:
        """Falls back to default when no higher quality is available."""
        thumbnails = {
            "default": {"url": "https://img/default.jpg"},
        }
        assert _select_best_thumbnail(thumbnails) == "https://img/default.jpg"

    def test_returns_none_for_empty_dict(self) -> None:
        """Returns None when thumbnails dict is empty."""
        assert _select_best_thumbnail({}) is None

    def test_skips_entries_without_url(self) -> None:
        """Skips thumbnail entries that have no url key."""
        thumbnails = {
            "maxres": {"width": 1280},
            "high": {"url": "https://img/high.jpg"},
        }
        assert _select_best_thumbnail(thumbnails) == "https://img/high.jpg"


class TestParseSearchResults:
    """Test parsing of search.list response items."""

    def test_parses_video_items(self) -> None:
        """Correctly parses video items from search response."""
        results = _parse_search_results(SAMPLE_SEARCH_RESPONSE["items"])
        assert len(results) == 2
        assert results[0]["video_id"] == "abc123"
        assert results[0]["title"] == "AI Agents para Fintech na America Latina"
        assert results[1]["video_id"] == "def456"

    def test_skips_items_without_video_id(self) -> None:
        """Skips items that lack a videoId (e.g., channels or playlists)."""
        items = [
            {"id": {"kind": "youtube#channel", "channelId": "UCxxx"}, "snippet": {}},
            {"id": {"kind": "youtube#video", "videoId": "valid1"}, "snippet": {"title": "Valid"}},
        ]
        results = _parse_search_results(items)
        assert len(results) == 1
        assert results[0]["video_id"] == "valid1"

    def test_handles_empty_items(self) -> None:
        """Returns empty list for empty items."""
        assert _parse_search_results([]) == []


class TestFetchYouTubeVideos:
    """Test the main fetch function that queries YouTube Data API v3."""

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_fetch_success(self, mock_key: MagicMock) -> None:
        """Successful fetch parses both search and stats responses."""
        mock_key.return_value = "fake_youtube_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = SAMPLE_SEARCH_RESPONSE

        stats_resp = MagicMock()
        stats_resp.raise_for_status = MagicMock()
        stats_resp.json.return_value = SAMPLE_VIDEOS_RESPONSE

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = [search_resp, stats_resp]
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            result = fetch_youtube_videos("AI fintech LATAM")

        assert len(result) == 2
        assert all(isinstance(v, YouTubeVideo) for v in result)

        # First video
        assert result[0].video_id == "abc123"
        assert result[0].title == "AI Agents para Fintech na America Latina"
        assert result[0].channel_title == "Tech LATAM"
        assert result[0].view_count == 150000
        assert result[0].like_count == 4500
        assert result[0].comment_count == 320
        assert result[0].duration == "PT15M32S"
        assert result[0].url == "https://www.youtube.com/watch?v=abc123"
        assert result[0].embed_url == "https://www.youtube.com/embed/abc123"
        assert result[0].thumbnail_url == "https://i.ytimg.com/vi/abc123/hqdefault.jpg"

        # Second video
        assert result[1].video_id == "def456"
        assert result[1].view_count == 25000
        assert result[1].thumbnail_url == "https://i.ytimg.com/vi/def456/default.jpg"

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_returns_empty_when_no_api_key(self, mock_key: MagicMock) -> None:
        """Returns empty list when API key is not configured."""
        mock_key.return_value = None
        result = fetch_youtube_videos("test query")
        assert result == []

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_empty_query_returns_empty_list(self, mock_key: MagicMock) -> None:
        """Empty query returns empty list without API call."""
        mock_key.return_value = "fake_key"
        result = fetch_youtube_videos("")
        assert result == []

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_returns_empty_on_http_error(self, mock_key: MagicMock) -> None:
        """Returns empty list on HTTP status error (e.g., 403 quota exceeded)."""
        mock_key.return_value = "fake_key"

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "403 Forbidden",
                request=MagicMock(),
                response=MagicMock(),
            )
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            result = fetch_youtube_videos("test query")

        assert result == []

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_returns_empty_on_timeout(self, mock_key: MagicMock) -> None:
        """Returns empty list on timeout."""
        mock_key.return_value = "fake_key"

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            result = fetch_youtube_videos("test query")

        assert result == []

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_returns_empty_on_no_search_results(self, mock_key: MagicMock) -> None:
        """Returns empty list when search returns no items."""
        mock_key.return_value = "fake_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"items": []}

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = search_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            result = fetch_youtube_videos("obscure query no results")

        assert result == []

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_published_after_parameter_formatting(self, mock_key: MagicMock) -> None:
        """published_after datetime is formatted as ISO 8601 for the API."""
        mock_key.return_value = "fake_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"items": []}

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = search_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            published_after = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
            fetch_youtube_videos("test", published_after=published_after)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params["publishedAfter"] == "2026-03-01T00:00:00Z"

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_order_parameter_passed(self, mock_key: MagicMock) -> None:
        """order parameter is passed to the search API."""
        mock_key.return_value = "fake_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"items": []}

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = search_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            fetch_youtube_videos("test", order="viewCount")

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params["order"] == "viewCount"

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_max_results_capped_at_50(self, mock_key: MagicMock) -> None:
        """max_results is capped at 50 (YouTube API limit)."""
        mock_key.return_value = "fake_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"items": []}

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = search_resp
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            fetch_youtube_videos("test", max_results=100)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params["maxResults"] == 50

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_stats_call_uses_comma_separated_ids(self, mock_key: MagicMock) -> None:
        """Videos.list call uses comma-separated video IDs."""
        mock_key.return_value = "fake_key"

        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = SAMPLE_SEARCH_RESPONSE

        stats_resp = MagicMock()
        stats_resp.raise_for_status = MagicMock()
        stats_resp.json.return_value = SAMPLE_VIDEOS_RESPONSE

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = [search_resp, stats_resp]
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            fetch_youtube_videos("test")

        # Second call should be the stats call
        stats_call = mock_client.get.call_args_list[1]
        stats_params = stats_call.kwargs.get("params") or stats_call[1].get("params", {})
        assert stats_params["id"] == "abc123,def456"
        assert stats_params["part"] == "statistics,contentDetails"

    @patch("apps.agents.sources.youtube._get_api_key")
    def test_returns_empty_on_unexpected_error(self, mock_key: MagicMock) -> None:
        """Returns empty list on unexpected exceptions."""
        mock_key.return_value = "fake_key"

        with patch("apps.agents.sources.youtube.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = RuntimeError("Unexpected")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            result = fetch_youtube_videos("test")

        assert result == []
