"""Tests for Twitter/X API v2 source module.

Tests TwitterPost dataclass, fetch_twitter_search, and
fetch_twitter_user_timeline functions that interact with the Twitter API v2
for collecting tweets relevant to LATAM tech intelligence.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.twitter import (
    TWITTER_API_BASE,
    TWITTER_SEARCH_ENDPOINT,
    TwitterPost,
    fetch_twitter_search,
    fetch_twitter_user_timeline,
)


# ---------------------------------------------------------------------------
# Sample mock responses
# ---------------------------------------------------------------------------

SAMPLE_SEARCH_RESPONSE = {
    "data": [
        {
            "id": "1234567890",
            "text": "Startup brasileira levanta US$ 50M em Serie B para expandir na LATAM",
            "author_id": "111",
            "created_at": "2026-02-15T14:30:00.000Z",
            "public_metrics": {
                "like_count": 245,
                "reply_count": 12,
                "retweet_count": 89,
                "quote_count": 15,
                "impression_count": 50000,
            },
            "entities": {
                "urls": [
                    {
                        "start": 50,
                        "end": 73,
                        "url": "https://t.co/abc123",
                        "expanded_url": "https://techcrunch.com/startup-latam-series-b",
                        "display_url": "techcrunch.com/startup-latam-...",
                    }
                ]
            },
            "attachments": {
                "media_keys": ["media_001"],
            },
        },
        {
            "id": "9876543210",
            "text": "Nova plataforma open-source para fintech na America Latina",
            "author_id": "222",
            "created_at": "2026-02-14T10:00:00.000Z",
            "public_metrics": {
                "like_count": 120,
                "reply_count": 5,
                "retweet_count": 30,
                "quote_count": 8,
                "impression_count": 25000,
            },
        },
    ],
    "includes": {
        "users": [
            {
                "id": "111",
                "name": "Maria Santos",
                "username": "maria_tech",
                "public_metrics": {
                    "followers_count": 15000,
                    "following_count": 500,
                    "tweet_count": 3200,
                },
            },
            {
                "id": "222",
                "name": "Tech LATAM",
                "username": "techlatam",
                "public_metrics": {
                    "followers_count": 8500,
                    "following_count": 200,
                    "tweet_count": 1500,
                },
            },
        ],
        "media": [
            {
                "media_key": "media_001",
                "type": "photo",
                "url": "https://pbs.twimg.com/media/photo123.jpg",
            }
        ],
    },
}

SAMPLE_TIMELINE_RESPONSE = {
    "data": [
        {
            "id": "5555555555",
            "text": "Lancamos nossa API v2 hoje! Confira a documentacao.",
            "author_id": "111",
            "created_at": "2026-02-16T09:00:00.000Z",
            "public_metrics": {
                "like_count": 50,
                "reply_count": 3,
                "retweet_count": 10,
                "quote_count": 2,
                "impression_count": 8000,
            },
        },
    ],
    "includes": {
        "users": [
            {
                "id": "111",
                "name": "Maria Santos",
                "username": "maria_tech",
                "public_metrics": {
                    "followers_count": 15000,
                },
            },
        ],
    },
}


class TestTwitterPost:
    """Test TwitterPost dataclass and content hash generation."""

    def test_content_hash_computed_from_url(self) -> None:
        """content_hash is computed as MD5 of the tweet URL."""
        url = "https://x.com/maria_tech/status/1234567890"
        post = TwitterPost(
            text="Test tweet",
            url=url,
            source_name="twitter_test",
        )
        expected_hash = hashlib.md5(url.encode()).hexdigest()
        assert post.content_hash == expected_hash

    def test_all_fields_populated(self) -> None:
        """All fields populated correctly."""
        created_at = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
        post = TwitterPost(
            text="Full tweet with all fields",
            url="https://x.com/maria_tech/status/123",
            source_name="twitter_latam",
            author_handle="maria_tech",
            author_display_name="Maria Santos",
            author_followers=15000,
            like_count=245,
            reply_count=12,
            retweet_count=89,
            quote_count=15,
            impression_count=50000,
            created_at=created_at,
            external_url="https://techcrunch.com/article",
            image_url="https://pbs.twimg.com/media/photo.jpg",
        )

        assert post.text == "Full tweet with all fields"
        assert post.url == "https://x.com/maria_tech/status/123"
        assert post.source_name == "twitter_latam"
        assert post.author_handle == "maria_tech"
        assert post.author_display_name == "Maria Santos"
        assert post.author_followers == 15000
        assert post.like_count == 245
        assert post.reply_count == 12
        assert post.retweet_count == 89
        assert post.quote_count == 15
        assert post.impression_count == 50000
        assert post.created_at == created_at
        assert post.external_url == "https://techcrunch.com/article"
        assert post.image_url == "https://pbs.twimg.com/media/photo.jpg"
        assert post.content_hash != ""

    def test_default_values(self) -> None:
        """Default values set correctly (counts=0, optionals=None)."""
        post = TwitterPost(
            text="Minimal tweet",
            url="https://x.com/test/status/1",
            source_name="test",
        )

        assert post.author_handle is None
        assert post.author_display_name is None
        assert post.author_followers == 0
        assert post.like_count == 0
        assert post.reply_count == 0
        assert post.retweet_count == 0
        assert post.quote_count == 0
        assert post.impression_count == 0
        assert post.created_at is None
        assert post.external_url is None
        assert post.image_url is None

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Custom content_hash is preserved."""
        custom_hash = "custom_hash_12345"
        post = TwitterPost(
            text="Tweet with custom hash",
            url="https://x.com/test/status/1",
            source_name="test",
            content_hash=custom_hash,
        )

        assert post.content_hash == custom_hash


class TestFetchTwitterSearch:
    """Test the search function that queries Twitter API v2."""

    def _make_source(
        self,
        name: str = "twitter_test",
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Twitter."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=TWITTER_SEARCH_ENDPOINT,
            params={},
        )

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_success(
        self, mock_token: MagicMock
    ) -> None:
        """Successful search fetch parses response into TwitterPost objects."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_SEARCH_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        assert len(result) == 2
        assert all(isinstance(post, TwitterPost) for post in result)

        # Check first tweet
        assert result[0].text == (
            "Startup brasileira levanta US$ 50M em Serie B para expandir na LATAM"
        )
        assert result[0].author_handle == "maria_tech"
        assert result[0].author_display_name == "Maria Santos"
        assert result[0].author_followers == 15000
        assert result[0].like_count == 245
        assert result[0].reply_count == 12
        assert result[0].retweet_count == 89
        assert result[0].quote_count == 15
        assert result[0].impression_count == 50000
        assert result[0].url == "https://x.com/maria_tech/status/1234567890"

        # Check second tweet
        assert result[1].text == (
            "Nova plataforma open-source para fintech na America Latina"
        )
        assert result[1].author_handle == "techlatam"
        assert result[1].like_count == 120

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_returns_empty_on_auth_failure(
        self, mock_token: MagicMock
    ) -> None:
        """Returns empty list when Bearer token is not configured."""
        mock_token.return_value = None

        client = MagicMock(spec=httpx.Client)
        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_returns_empty_on_rate_limit(
        self, mock_token: MagicMock
    ) -> None:
        """Returns empty list on 429 rate limit error."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(),
        )

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        assert result == []

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_returns_empty_on_timeout(
        self, mock_token: MagicMock
    ) -> None:
        """Returns empty list on timeout."""
        mock_token.return_value = "fake_bearer_token"

        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = httpx.TimeoutException("Request timeout")

        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        assert result == []

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_extracts_external_url(
        self, mock_token: MagicMock
    ) -> None:
        """Extracts external URL from entities.urls, filtering Twitter links."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_SEARCH_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        # First tweet has an external URL
        assert result[0].external_url == (
            "https://techcrunch.com/startup-latam-series-b"
        )
        # Second tweet has no entities.urls
        assert result[1].external_url is None

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_search_extracts_image(
        self, mock_token: MagicMock
    ) -> None:
        """Extracts image URL from media attachments via includes.media."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_SEARCH_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_search(source, client, "latam startups")

        # First tweet has a media attachment
        assert result[0].image_url == (
            "https://pbs.twimg.com/media/photo123.jpg"
        )
        # Second tweet has no media attachments
        assert result[1].image_url is None

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_empty_query_returns_empty_list(
        self, mock_token: MagicMock
    ) -> None:
        """Empty query returns empty list without API call."""
        mock_token.return_value = "fake_bearer_token"

        client = MagicMock(spec=httpx.Client)
        source = self._make_source()
        result = fetch_twitter_search(source, client, "")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_respects_max_results_parameter(
        self, mock_token: MagicMock
    ) -> None:
        """max_results parameter passed to API call."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": []}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        fetch_twitter_search(source, client, "test", max_results=50)

        call_kwargs = client.get.call_args.kwargs
        assert call_kwargs["params"]["max_results"] == 50
        assert call_kwargs["params"]["query"] == "test"

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_correct_auth_headers_sent(
        self, mock_token: MagicMock
    ) -> None:
        """Correct Authorization headers sent to Twitter API."""
        mock_token.return_value = "my_bearer_xyz"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": []}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        fetch_twitter_search(source, client, "test")

        call_kwargs = client.get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_bearer_xyz"

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_empty_data_response_returns_empty_list(
        self, mock_token: MagicMock
    ) -> None:
        """Response with no 'data' key returns empty list."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"meta": {"result_count": 0}}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_search(source, client, "test")

        assert result == []


class TestFetchTwitterUserTimeline:
    """Test the timeline function that fetches a user's tweets."""

    def _make_source(
        self,
        name: str = "twitter_timeline_test",
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Twitter timeline."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=None,
            params={},
        )

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_fetch_twitter_user_timeline_success(
        self, mock_token: MagicMock
    ) -> None:
        """Successful timeline fetch parses response into TwitterPost objects."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_TIMELINE_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_user_timeline(source, client, "111")

        assert len(result) == 1
        assert isinstance(result[0], TwitterPost)
        assert result[0].text == (
            "Lancamos nossa API v2 hoje! Confira a documentacao."
        )
        assert result[0].author_handle == "maria_tech"
        assert result[0].author_display_name == "Maria Santos"
        assert result[0].like_count == 50
        assert result[0].url == "https://x.com/maria_tech/status/5555555555"

        # Verify correct endpoint was called
        call_args = client.get.call_args
        assert call_args[0][0] == f"{TWITTER_API_BASE}/users/111/tweets"

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_empty_user_id_returns_empty_list(
        self, mock_token: MagicMock
    ) -> None:
        """Empty user_id returns empty list without API call."""
        mock_token.return_value = "fake_bearer_token"

        client = MagicMock(spec=httpx.Client)
        source = self._make_source()
        result = fetch_twitter_user_timeline(source, client, "")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_timeline_returns_empty_on_auth_failure(
        self, mock_token: MagicMock
    ) -> None:
        """Returns empty list when Bearer token is not configured."""
        mock_token.return_value = None

        client = MagicMock(spec=httpx.Client)
        source = self._make_source()
        result = fetch_twitter_user_timeline(source, client, "111")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.twitter._get_bearer_token")
    def test_timeline_returns_empty_on_http_error(
        self, mock_token: MagicMock
    ) -> None:
        """Returns empty list on HTTP error."""
        mock_token.return_value = "fake_bearer_token"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=MagicMock(),
        )

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_twitter_user_timeline(source, client, "111")

        assert result == []
