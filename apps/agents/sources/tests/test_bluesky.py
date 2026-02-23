"""Tests for Bluesky AT Protocol source module.

Tests BlueskyPost dataclass, build_post_url, parse_bluesky_post, and
fetch_bluesky_search functions that interact with the AT Protocol public API.
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.bluesky import (
    BLUESKY_SEARCH_ENDPOINT,
    BlueskyPost,
    _extract_media_urls,
    build_post_url,
    fetch_bluesky_search,
    parse_bluesky_post,
)


class TestBlueskyPost:
    """Test BlueskyPost dataclass and content hash generation."""

    def test_content_hash_from_external_url(self) -> None:
        """content_hash generated from external_url when present."""
        post = BlueskyPost(
            text="Check out this article",
            url="https://bsky.app/profile/test.bsky.social/post/abc123",
            source_name="bluesky_test",
            external_url="https://example.com/article",
        )
        # Hash should be MD5 of external_url
        import hashlib

        expected_hash = hashlib.md5(
            "https://example.com/article".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_content_hash_from_url_when_no_external_url(self) -> None:
        """content_hash generated from url when no external_url."""
        post = BlueskyPost(
            text="Text-only post",
            url="https://bsky.app/profile/test.bsky.social/post/abc123",
            source_name="bluesky_test",
            external_url=None,
        )
        # Hash should be MD5 of url
        import hashlib

        expected_hash = hashlib.md5(
            "https://bsky.app/profile/test.bsky.social/post/abc123".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_all_fields_populated(self) -> None:
        """All fields populated correctly."""
        created_at = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        post = BlueskyPost(
            text="Full post with all fields",
            url="https://bsky.app/profile/maria.bsky.social/post/abc123",
            source_name="bluesky_latam",
            author_handle="maria.bsky.social",
            author_display_name="Maria Santos",
            external_url="https://blog.example.com/post",
            like_count=42,
            reply_count=8,
            repost_count=15,
            created_at=created_at,
        )

        assert post.text == "Full post with all fields"
        assert post.url == "https://bsky.app/profile/maria.bsky.social/post/abc123"
        assert post.source_name == "bluesky_latam"
        assert post.author_handle == "maria.bsky.social"
        assert post.author_display_name == "Maria Santos"
        assert post.external_url == "https://blog.example.com/post"
        assert post.like_count == 42
        assert post.reply_count == 8
        assert post.repost_count == 15
        assert post.created_at == created_at
        assert post.content_hash != ""

    def test_default_values(self) -> None:
        """Default values set correctly (counts=0, optionals=None)."""
        post = BlueskyPost(
            text="Minimal post",
            url="https://bsky.app/profile/test.bsky.social/post/123",
            source_name="test",
        )

        assert post.author_handle is None
        assert post.author_display_name is None
        assert post.external_url is None
        assert post.like_count == 0
        assert post.reply_count == 0
        assert post.repost_count == 0
        assert post.created_at is None
        assert post.image_url is None
        assert post.video_url is None

    def test_image_url_and_video_url_stored(self) -> None:
        """image_url and video_url stored when provided."""
        post = BlueskyPost(
            text="Post with media",
            url="https://bsky.app/profile/test.bsky.social/post/123",
            source_name="test",
            image_url="https://cdn.bsky.app/img/thumb.jpg",
            video_url="https://video.bsky.app/watch/playlist.m3u8",
        )
        assert post.image_url == "https://cdn.bsky.app/img/thumb.jpg"
        assert post.video_url == "https://video.bsky.app/watch/playlist.m3u8"

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Custom content_hash is preserved."""
        custom_hash = "custom_hash_12345"
        post = BlueskyPost(
            text="Post with custom hash",
            url="https://bsky.app/profile/test.bsky.social/post/abc",
            source_name="test",
            content_hash=custom_hash,
        )

        assert post.content_hash == custom_hash

    def test_text_with_various_lengths(self) -> None:
        """Text field handles various lengths correctly."""
        # Short text
        post_short = BlueskyPost(
            text="Hi",
            url="https://bsky.app/profile/test.bsky.social/post/1",
            source_name="test",
        )
        assert post_short.text == "Hi"

        # Long text (300 chars)
        long_text = "A" * 300
        post_long = BlueskyPost(
            text=long_text,
            url="https://bsky.app/profile/test.bsky.social/post/2",
            source_name="test",
        )
        assert post_long.text == long_text
        assert len(post_long.text) == 300

        # Unicode text
        unicode_text = "Olá! São Paulo está incrível 🇧🇷"
        post_unicode = BlueskyPost(
            text=unicode_text,
            url="https://bsky.app/profile/test.bsky.social/post/3",
            source_name="test",
        )
        assert post_unicode.text == unicode_text

    def test_empty_text(self) -> None:
        """Empty text is allowed (edge case)."""
        post = BlueskyPost(
            text="",
            url="https://bsky.app/profile/test.bsky.social/post/1",
            source_name="test",
        )
        assert post.text == ""


class TestExtractMediaUrls:
    """Test _extract_media_urls for Bluesky embed types."""

    def test_images_view_extracts_first_thumb(self) -> None:
        """app.bsky.embed.images#view → first image thumb."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [
                    {"thumb": "https://cdn.bsky.app/img/thumb1.jpg", "fullsize": "https://cdn.bsky.app/img/full1.jpg"},
                    {"thumb": "https://cdn.bsky.app/img/thumb2.jpg"},
                ],
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img == "https://cdn.bsky.app/img/thumb1.jpg"
        assert vid is None

    def test_images_view_falls_back_to_fullsize(self) -> None:
        """Falls back to fullsize when thumb is missing."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [
                    {"fullsize": "https://cdn.bsky.app/img/full.jpg"},
                ],
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img == "https://cdn.bsky.app/img/full.jpg"

    def test_external_view_extracts_thumb(self) -> None:
        """app.bsky.embed.external#view → external thumb."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.external#view",
                "external": {
                    "uri": "https://example.com/article",
                    "title": "Article",
                    "thumb": "https://cdn.bsky.app/img/external-thumb.jpg",
                },
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img == "https://cdn.bsky.app/img/external-thumb.jpg"
        assert vid is None

    def test_video_view_extracts_thumbnail_and_playlist(self) -> None:
        """app.bsky.embed.video#view → thumbnail + playlist."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.video#view",
                "thumbnail": "https://video.bsky.app/thumb.jpg",
                "playlist": "https://video.bsky.app/watch/abc/playlist.m3u8",
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img == "https://video.bsky.app/thumb.jpg"
        assert vid == "https://video.bsky.app/watch/abc/playlist.m3u8"

    def test_record_with_media_unwraps_inner_embed(self) -> None:
        """app.bsky.embed.recordWithMedia#view → unwraps inner media."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.recordWithMedia#view",
                "media": {
                    "$type": "app.bsky.embed.images#view",
                    "images": [
                        {"thumb": "https://cdn.bsky.app/img/quoted.jpg"},
                    ],
                },
                "record": {"$type": "app.bsky.embed.record#view"},
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img == "https://cdn.bsky.app/img/quoted.jpg"
        assert vid is None

    def test_no_embed_returns_none_tuple(self) -> None:
        """Post with no embed returns (None, None)."""
        raw_post = {}
        img, vid = _extract_media_urls(raw_post)
        assert img is None
        assert vid is None

    def test_empty_embed_returns_none_tuple(self) -> None:
        """Post with empty embed dict returns (None, None)."""
        raw_post = {"embed": {}}
        img, vid = _extract_media_urls(raw_post)
        assert img is None
        assert vid is None

    def test_unknown_embed_type_returns_none_tuple(self) -> None:
        """Unknown embed type returns (None, None)."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.unknown#view",
                "data": "something",
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img is None
        assert vid is None

    def test_empty_images_list(self) -> None:
        """images#view with empty images list returns (None, None)."""
        raw_post = {
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [],
            }
        }
        img, vid = _extract_media_urls(raw_post)
        assert img is None
        assert vid is None


class TestBuildPostUrl:
    """Test URL building from author handle and post record key."""

    def test_standard_handle_and_rkey(self) -> None:
        """Standard handle and rkey produce correct URL."""
        url = build_post_url("maria.bsky.social", "3abc123")
        assert url == "https://bsky.app/profile/maria.bsky.social/post/3abc123"

    def test_handle_with_custom_domain(self) -> None:
        """Handle with custom domain works correctly."""
        url = build_post_url("maria.tech", "3def456")
        assert url == "https://bsky.app/profile/maria.tech/post/3def456"

    def test_empty_handle_edge_case(self) -> None:
        """Empty handle produces malformed but predictable URL."""
        url = build_post_url("", "3abc123")
        assert url == "https://bsky.app/profile//post/3abc123"

    def test_empty_rkey_edge_case(self) -> None:
        """Empty rkey produces malformed but predictable URL."""
        url = build_post_url("test.bsky.social", "")
        assert url == "https://bsky.app/profile/test.bsky.social/post/"


class TestParseBlueskyPost:
    """Test parsing of AT Protocol post objects into BlueskyPost."""

    def test_parses_complete_post(self) -> None:
        """Parses complete post with all fields."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "cid": "bafyreiabc123",
            "author": {
                "did": "did:plc:abc123",
                "handle": "maria.bsky.social",
                "displayName": "Maria Santos",
            },
            "record": {
                "text": "Just shipped our new AI feature for LATAM fintech.",
                "createdAt": "2026-02-15T14:30:00.000Z",
                "embed": {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": "https://blog.fintechbr.com/ai-feature-launch",
                        "title": "Launching AI-Powered Credit Analysis",
                        "description": "How we built an AI credit system",
                    },
                },
            },
            "likeCount": 42,
            "replyCount": 8,
            "repostCount": 15,
        }

        post = parse_bluesky_post(raw_post, "bluesky_latam")

        assert post is not None
        assert post.text == "Just shipped our new AI feature for LATAM fintech."
        assert post.url == "https://bsky.app/profile/maria.bsky.social/post/3abc123"
        assert post.source_name == "bluesky_latam"
        assert post.author_handle == "maria.bsky.social"
        assert post.author_display_name == "Maria Santos"
        assert post.external_url == "https://blog.fintechbr.com/ai-feature-launch"
        assert post.like_count == 42
        assert post.reply_count == 8
        assert post.repost_count == 15
        assert post.created_at == datetime(
            2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc
        )

    def test_extracts_external_url_from_embed(self) -> None:
        """Extracts external_url from embed.external.uri."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Check this out",
                "createdAt": "2026-02-15T10:00:00.000Z",
                "embed": {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": "https://example.com/article",
                    },
                },
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.external_url == "https://example.com/article"

    def test_missing_embed_produces_none_external_url(self) -> None:
        """Missing embed produces None external_url."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Text-only post",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.external_url is None

    def test_parses_author_handle_and_display_name(self) -> None:
        """Parses author handle and display name correctly."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {
                "handle": "techdev.bsky.social",
                "displayName": "Tech Dev BR",
            },
            "record": {
                "text": "Test post",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.author_handle == "techdev.bsky.social"
        assert post.author_display_name == "Tech Dev BR"

    def test_parses_engagement_counts(self) -> None:
        """Parses like/reply/repost counts correctly."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Popular post",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
            "likeCount": 100,
            "replyCount": 25,
            "repostCount": 50,
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.like_count == 100
        assert post.reply_count == 25
        assert post.repost_count == 50

    def test_parses_created_at_timestamp(self) -> None:
        """Parses created_at timestamp correctly."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Timestamped post",
                "createdAt": "2026-02-14T10:00:00.000Z",
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.created_at == datetime(
            2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc
        )

    def test_missing_required_fields_returns_none(self) -> None:
        """Missing required fields returns None."""
        # Missing 'uri'
        raw_post_no_uri = {
            "author": {"handle": "test.bsky.social"},
            "record": {"text": "Test", "createdAt": "2026-02-15T10:00:00.000Z"},
        }
        assert parse_bluesky_post(raw_post_no_uri, "test") is None

        # Missing 'author'
        raw_post_no_author = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "record": {"text": "Test", "createdAt": "2026-02-15T10:00:00.000Z"},
        }
        assert parse_bluesky_post(raw_post_no_author, "test") is None

        # Missing 'record'
        raw_post_no_record = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
        }
        assert parse_bluesky_post(raw_post_no_record, "test") is None

        # Missing 'record.text'
        raw_post_no_text = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {"createdAt": "2026-02-15T10:00:00.000Z"},
        }
        assert parse_bluesky_post(raw_post_no_text, "test") is None

    def test_malformed_timestamp_handled_gracefully(self) -> None:
        """Malformed timestamp sets created_at to None."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Post with bad timestamp",
                "createdAt": "invalid-timestamp",
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.text == "Post with bad timestamp"
        assert post.created_at is None

    def test_builds_correct_bsky_app_permalink(self) -> None:
        """Builds correct bsky.app permalink URL from AT URI."""
        raw_post = {
            "uri": "at://did:plc:xyz789/app.bsky.feed.post/3xyz789",
            "author": {"handle": "custom.domain.com"},
            "record": {
                "text": "Test permalink",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
        }

        post = parse_bluesky_post(raw_post, "test")

        assert post is not None
        assert post.url == "https://bsky.app/profile/custom.domain.com/post/3xyz789"

    def test_extracts_image_from_images_embed(self) -> None:
        """parse_bluesky_post passes image_url from images embed."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Post with image",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [
                    {"thumb": "https://cdn.bsky.app/img/photo.jpg"},
                ],
            },
        }
        post = parse_bluesky_post(raw_post, "test")
        assert post is not None
        assert post.image_url == "https://cdn.bsky.app/img/photo.jpg"
        assert post.video_url is None

    def test_extracts_video_from_video_embed(self) -> None:
        """parse_bluesky_post passes video_url from video embed."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Post with video",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
            "embed": {
                "$type": "app.bsky.embed.video#view",
                "thumbnail": "https://video.bsky.app/thumb.jpg",
                "playlist": "https://video.bsky.app/watch/playlist.m3u8",
            },
        }
        post = parse_bluesky_post(raw_post, "test")
        assert post is not None
        assert post.image_url == "https://video.bsky.app/thumb.jpg"
        assert post.video_url == "https://video.bsky.app/watch/playlist.m3u8"

    def test_no_embed_produces_none_media(self) -> None:
        """Post with no embed has None image_url and video_url."""
        raw_post = {
            "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
            "author": {"handle": "test.bsky.social"},
            "record": {
                "text": "Text-only post",
                "createdAt": "2026-02-15T10:00:00.000Z",
            },
        }
        post = parse_bluesky_post(raw_post, "test")
        assert post is not None
        assert post.image_url is None
        assert post.video_url is None


class TestFetchBlueskySearch:
    """Test the fetch function that queries AT Protocol search API."""

    def _make_source(
        self,
        name: str = "bluesky_test",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Bluesky."""
        return DataSourceConfig(
            name=name,
            source_type="bluesky",
            url=BLUESKY_SEARCH_ENDPOINT,
            max_items=max_items,
            params={},
        )

    def test_successful_fetch_with_mocked_response(self) -> None:
        """Successful fetch with mocked response returns parsed posts."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {
                    "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
                    "author": {
                        "handle": "maria.bsky.social",
                        "displayName": "Maria Santos",
                    },
                    "record": {
                        "text": "Test post 1",
                        "createdAt": "2026-02-15T14:30:00.000Z",
                    },
                    "likeCount": 10,
                    "replyCount": 2,
                    "repostCount": 3,
                },
                {
                    "uri": "at://did:plc:def456/app.bsky.feed.post/3def456",
                    "author": {
                        "handle": "techdev.bsky.social",
                        "displayName": "Tech Dev BR",
                    },
                    "record": {
                        "text": "Test post 2",
                        "createdAt": "2026-02-14T10:00:00.000Z",
                    },
                    "likeCount": 5,
                },
            ],
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "latam startups")

        assert len(results) == 2
        assert all(isinstance(p, BlueskyPost) for p in results)
        assert results[0].text == "Test post 1"
        assert results[0].author_handle == "maria.bsky.social"
        assert results[1].text == "Test post 2"
        assert results[1].author_handle == "techdev.bsky.social"

    def test_empty_results_returns_empty_list(self) -> None:
        """Empty results returns empty list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": []}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "nonexistent query")

        assert results == []

    def test_http_error_returns_empty_list(self) -> None:
        """HTTP error returns empty list."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.HTTPError("Network error")

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "test query")

        assert results == []

    def test_timeout_returns_empty_list(self) -> None:
        """Timeout returns empty list."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "test query")

        assert results == []

    def test_respects_limit_parameter(self) -> None:
        """Respects limit parameter in API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": []}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        fetch_bluesky_search(source, mock_client, "test", limit=10)

        # Verify API was called with correct limit
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["limit"] == 10

    def test_correct_query_parameter_in_api_call(self) -> None:
        """Correct query parameter passed to API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": []}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        fetch_bluesky_search(source, mock_client, "latam fintech")

        # Verify API was called with correct query
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["q"] == "latam fintech"

    def test_empty_query_returns_empty_list(self) -> None:
        """Empty query returns empty list without API call."""
        mock_client = MagicMock(spec=httpx.Client)

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "")

        assert results == []
        mock_client.get.assert_not_called()

    def test_malformed_response_handled_gracefully(self) -> None:
        """Malformed response handled gracefully."""
        # Response missing 'posts' key
        mock_response = MagicMock()
        mock_response.json.return_value = {"cursor": "abc"}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "test")

        assert results == []

    def test_skips_posts_that_fail_parsing(self) -> None:
        """Skips posts that fail parsing (returns partial results)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {
                    "uri": "at://did:plc:abc123/app.bsky.feed.post/3abc123",
                    "author": {"handle": "valid.bsky.social"},
                    "record": {
                        "text": "Valid post",
                        "createdAt": "2026-02-15T10:00:00.000Z",
                    },
                },
                {
                    # Missing required 'record' field - should be skipped
                    "uri": "at://did:plc:def456/app.bsky.feed.post/3def456",
                    "author": {"handle": "invalid.bsky.social"},
                },
                {
                    "uri": "at://did:plc:ghi789/app.bsky.feed.post/3ghi789",
                    "author": {"handle": "another.bsky.social"},
                    "record": {
                        "text": "Another valid post",
                        "createdAt": "2026-02-15T11:00:00.000Z",
                    },
                },
            ],
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = self._make_source()
        results = fetch_bluesky_search(source, mock_client, "test")

        # Should return only the 2 valid posts, skipping the malformed one
        assert len(results) == 2
        assert results[0].text == "Valid post"
        assert results[1].text == "Another valid post"
