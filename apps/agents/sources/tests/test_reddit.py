"""Tests for shared Reddit API source module.

Tests RedditPost dataclass, authenticate_reddit, and fetch_subreddit_posts
functions that interact with the Reddit OAuth2 API for collecting posts from
subreddits relevant to LATAM tech intelligence.
"""

import base64
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.reddit import (
    REDDIT_API_BASE,
    REDDIT_AUTH_URL,
    REDDIT_USER_AGENT,
    RedditPost,
    authenticate_reddit,
    fetch_subreddit_posts,
)

# Sample mock responses
SAMPLE_AUTH_RESPONSE = {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test",
    "token_type": "bearer",
    "expires_in": 86400,
    "scope": "read",
}

SAMPLE_LISTING_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Como usar FastAPI com async SQLAlchemy 2.0",
                    "url": "https://blog.example.com/fastapi-sqlalchemy",
                    "subreddit": "brdev",
                    "score": 245,
                    "num_comments": 42,
                    "created_utc": 1739750400.0,  # 2025-02-17T00:00:00Z
                    "selftext": "",
                    "author": "dev_br_user",
                    "permalink": "/r/brdev/comments/abc123/como_usar_fastapi/",
                    "is_self": False,
                }
            },
            {
                "data": {
                    "title": "[Discussão] Mercado de trabalho remoto para devs LATAM",
                    "url": "https://www.reddit.com/r/brdev/comments/def456/discussao_mercado/",
                    "subreddit": "brdev",
                    "score": 189,
                    "num_comments": 95,
                    "created_utc": 1739664000.0,
                    "selftext": "Quero saber como está o mercado para...",
                    "author": "tech_latam",
                    "permalink": "/r/brdev/comments/def456/discussao_mercado/",
                    "is_self": True,
                }
            },
        ]
    }
}


class TestRedditPost:
    """Test RedditPost dataclass initialization and content_hash generation."""

    def test_content_hash_from_external_url_for_link_posts(self) -> None:
        """Link posts hash the external URL for deduplication."""
        post = RedditPost(
            title="Test Article",
            url="https://techcrunch.com/article-123",
            source_name="reddit_brdev",
            subreddit="brdev",
            permalink="/r/brdev/comments/abc/test/",
        )
        # Should hash the external URL
        import hashlib

        expected_hash = hashlib.md5(
            "https://techcrunch.com/article-123".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_content_hash_uses_permalink_for_self_posts(self) -> None:
        """Self posts (URL starts with reddit.com) hash the permalink."""
        post = RedditPost(
            title="Discussion Thread",
            url="https://www.reddit.com/r/brdev/comments/xyz/discussion/",
            source_name="reddit_brdev",
            subreddit="brdev",
            permalink="/r/brdev/comments/xyz/discussion/",
        )
        # Should hash the permalink since URL is reddit.com
        import hashlib

        expected_hash = hashlib.md5(
            "/r/brdev/comments/xyz/discussion/".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_all_fields_populated_correctly(self) -> None:
        """All fields are stored correctly."""
        created_dt = datetime(2025, 2, 17, 10, 0, 0, tzinfo=timezone.utc)
        post = RedditPost(
            title="Test Title",
            url="https://example.com/test",
            source_name="reddit_test",
            subreddit="test_sub",
            score=100,
            num_comments=25,
            created_utc=created_dt,
            selftext="This is the post body",
            author="test_user",
            permalink="/r/test_sub/comments/abc/test_title/",
        )

        assert post.title == "Test Title"
        assert post.url == "https://example.com/test"
        assert post.source_name == "reddit_test"
        assert post.subreddit == "test_sub"
        assert post.score == 100
        assert post.num_comments == 25
        assert post.created_utc == created_dt
        assert post.selftext == "This is the post body"
        assert post.author == "test_user"
        assert post.permalink == "/r/test_sub/comments/abc/test_title/"

    def test_default_values(self) -> None:
        """Score and num_comments default to 0."""
        post = RedditPost(
            title="Minimal Post",
            url="https://example.com",
            source_name="reddit_test",
            subreddit="test",
        )

        assert post.score == 0
        assert post.num_comments == 0
        assert post.created_utc is None
        assert post.selftext is None
        assert post.author is None
        assert post.permalink == ""

    def test_custom_content_hash_preserved(self) -> None:
        """If content_hash is provided, it's preserved."""
        custom_hash = "custom1234567890abcdef"
        post = RedditPost(
            title="Test",
            url="https://example.com",
            source_name="reddit_test",
            subreddit="test",
            content_hash=custom_hash,
        )

        assert post.content_hash == custom_hash

    def test_empty_permalink_fallback(self) -> None:
        """When permalink is empty, falls back to URL for hashing."""
        post = RedditPost(
            title="Test",
            url="https://example.com/article",
            source_name="reddit_test",
            subreddit="test",
            permalink="",
        )
        # Should hash the URL since permalink is empty
        import hashlib

        expected_hash = hashlib.md5(
            "https://example.com/article".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_reddit_url_without_permalink_uses_url(self) -> None:
        """Reddit URL without permalink uses the URL itself for hashing."""
        post = RedditPost(
            title="Test",
            url="https://www.reddit.com/r/test/comments/abc/",
            source_name="reddit_test",
            subreddit="test",
            permalink="",
        )
        # No permalink, so should use URL
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.reddit.com/r/test/comments/abc/".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_selftext_field_handles_long_content(self) -> None:
        """Selftext can contain long markdown content."""
        long_text = "Lorem ipsum " * 500  # Very long text
        post = RedditPost(
            title="Long Post",
            url="https://www.reddit.com/r/test/comments/abc/",
            source_name="reddit_test",
            subreddit="test",
            selftext=long_text,
            permalink="/r/test/comments/abc/",
        )

        assert post.selftext == long_text
        assert len(post.selftext) > 1000


class TestAuthenticateReddit:
    """Test Reddit OAuth2 authentication flow."""

    @patch("os.getenv")
    def test_returns_none_when_client_id_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns None when REDDIT_CLIENT_ID env var is not set."""
        mock_getenv.side_effect = lambda key, default=None: (
            None if key == "REDDIT_CLIENT_ID" else "fake_secret"
        )
        client = MagicMock(spec=httpx.Client)

        result = authenticate_reddit(client)

        assert result is None
        client.post.assert_not_called()

    @patch("os.getenv")
    def test_returns_none_when_client_secret_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns None when REDDIT_CLIENT_SECRET env var is not set."""
        mock_getenv.side_effect = lambda key, default=None: (
            None if key == "REDDIT_CLIENT_SECRET" else "fake_id"
        )
        client = MagicMock(spec=httpx.Client)

        result = authenticate_reddit(client)

        assert result is None
        client.post.assert_not_called()

    @patch("os.getenv")
    def test_returns_none_when_both_env_vars_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns None when both env vars are missing."""
        mock_getenv.return_value = None
        client = MagicMock(spec=httpx.Client)

        result = authenticate_reddit(client)

        assert result is None
        client.post.assert_not_called()

    @patch("os.getenv")
    def test_successful_auth_returns_access_token(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful authentication returns access token string."""
        mock_getenv.side_effect = lambda key, default=None: {
            "REDDIT_CLIENT_ID": "test_client_id",
            "REDDIT_CLIENT_SECRET": "test_client_secret",
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_AUTH_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.post.return_value = mock_response

        result = authenticate_reddit(client)

        assert result == SAMPLE_AUTH_RESPONSE["access_token"]
        client.post.assert_called_once_with(
            REDDIT_AUTH_URL,
            auth=("test_client_id", "test_client_secret"),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": REDDIT_USER_AGENT},
        )

    @patch("os.getenv")
    def test_http_error_returns_none(self, mock_getenv: MagicMock) -> None:
        """HTTP errors during authentication return None."""
        mock_getenv.side_effect = lambda key, default=None: {
            "REDDIT_CLIENT_ID": "test_client_id",
            "REDDIT_CLIENT_SECRET": "test_client_secret",
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(),
        )

        client = MagicMock(spec=httpx.Client)
        client.post.return_value = mock_response

        result = authenticate_reddit(client)

        assert result is None

    @patch("os.getenv")
    def test_malformed_response_returns_none(
        self, mock_getenv: MagicMock
    ) -> None:
        """Malformed JSON response (no access_token key) returns None."""
        mock_getenv.side_effect = lambda key, default=None: {
            "REDDIT_CLIENT_ID": "test_client_id",
            "REDDIT_CLIENT_SECRET": "test_client_secret",
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_request"
        }  # Missing access_token

        client = MagicMock(spec=httpx.Client)
        client.post.return_value = mock_response

        result = authenticate_reddit(client)

        assert result is None

    @patch("os.getenv")
    def test_correct_auth_headers_sent(self, mock_getenv: MagicMock) -> None:
        """Correct HTTP Basic auth headers are sent."""
        client_id = "my_client_id"
        client_secret = "my_client_secret"

        mock_getenv.side_effect = lambda key, default=None: {
            "REDDIT_CLIENT_ID": client_id,
            "REDDIT_CLIENT_SECRET": client_secret,
        }.get(key, default)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_AUTH_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.post.return_value = mock_response

        authenticate_reddit(client)

        # Verify Basic auth was used
        call_kwargs = client.post.call_args.kwargs
        assert call_kwargs["auth"] == (client_id, client_secret)
        assert call_kwargs["data"] == {"grant_type": "client_credentials"}
        assert call_kwargs["headers"]["User-Agent"] == REDDIT_USER_AGENT


class TestFetchSubredditPosts:
    """Test fetching posts from subreddits via Reddit API."""

    def _make_source(
        self,
        name: str = "reddit_brdev",
        subreddit: str = "brdev",
        sort: str = "hot",
        time_filter: str = "week",
        limit: int = 25,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Reddit source."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=None,
            params={
                "subreddit": subreddit,
                "sort": sort,
                "time_filter": time_filter,
                "limit": limit,
            },
        )

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_returns_empty_list_when_auth_fails(
        self, mock_auth: MagicMock
    ) -> None:
        """Returns empty list when authentication fails."""
        mock_auth.return_value = None  # Auth failed
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_subreddit_posts(source, client, "brdev")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_successful_fetch_with_mocked_response(
        self, mock_auth: MagicMock
    ) -> None:
        """Successful fetch parses response into RedditPost objects."""
        mock_auth.return_value = "fake_access_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_LISTING_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_subreddit_posts(source, client, "brdev")

        assert len(result) == 2
        assert all(isinstance(post, RedditPost) for post in result)

        # Check first post (link post)
        assert result[0].title == "Como usar FastAPI com async SQLAlchemy 2.0"
        assert (
            result[0].url == "https://blog.example.com/fastapi-sqlalchemy"
        )
        assert result[0].subreddit == "brdev"
        assert result[0].score == 245
        assert result[0].num_comments == 42
        assert result[0].author == "dev_br_user"

        # Check second post (self post)
        assert (
            result[1].title
            == "[Discussão] Mercado de trabalho remoto para devs LATAM"
        )
        assert (
            result[1].url
            == "https://www.reddit.com/r/brdev/comments/def456/discussao_mercado/"
        )
        assert result[1].selftext == "Quero saber como está o mercado para..."

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_parses_score_num_comments_created_utc_correctly(
        self, mock_auth: MagicMock
    ) -> None:
        """Score, num_comments, and created_utc are parsed correctly."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_LISTING_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_subreddit_posts(source, client, "brdev")

        post = result[0]
        assert post.score == 245
        assert post.num_comments == 42
        assert post.created_utc is not None
        assert post.created_utc.year == 2025
        assert post.created_utc.month == 2
        assert post.created_utc.day == 17
        assert post.created_utc.tzinfo == timezone.utc

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_extracts_external_url_for_link_posts(
        self, mock_auth: MagicMock
    ) -> None:
        """Link posts use the external URL from the 'url' field."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_LISTING_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_subreddit_posts(source, client, "brdev")

        # First post is a link post
        assert not result[0].url.startswith("https://www.reddit.com")
        assert result[0].url == "https://blog.example.com/fastapi-sqlalchemy"

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_self_post_url_uses_reddit_permalink(
        self, mock_auth: MagicMock
    ) -> None:
        """Self posts use the Reddit URL from the 'url' field."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = SAMPLE_LISTING_RESPONSE

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_subreddit_posts(source, client, "brdev")

        # Second post is a self post
        assert result[1].url.startswith("https://www.reddit.com")

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_empty_subreddit_returns_empty_list(
        self, mock_auth: MagicMock
    ) -> None:
        """Empty subreddit parameter returns empty list."""
        mock_auth.return_value = "fake_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_subreddit_posts(source, client, "")

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_http_error_returns_empty_list(
        self, mock_auth: MagicMock
    ) -> None:
        """HTTP errors during fetch return empty list."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=MagicMock(),
        )

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        result = fetch_subreddit_posts(source, client, "brdev")

        assert result == []

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_respects_limit_parameter_in_api_call(
        self, mock_auth: MagicMock
    ) -> None:
        """Limit parameter is passed to the Reddit API."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        fetch_subreddit_posts(source, client, "brdev", limit=10)

        # Verify the API call includes limit=10
        call_args = client.get.call_args
        assert call_args is not None
        url = call_args[0][0]
        assert "limit=10" in url

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_correct_headers_sent(self, mock_auth: MagicMock) -> None:
        """Correct Authorization and User-Agent headers are sent."""
        access_token = "my_access_token_xyz"
        mock_auth.return_value = access_token

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        fetch_subreddit_posts(source, client, "brdev")

        call_kwargs = client.get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == f"Bearer {access_token}"
        assert call_kwargs["headers"]["User-Agent"] == REDDIT_USER_AGENT

    @patch("apps.agents.sources.reddit.authenticate_reddit")
    def test_respects_sort_and_time_filter_params(
        self, mock_auth: MagicMock
    ) -> None:
        """Sort and time_filter parameters are passed correctly."""
        mock_auth.return_value = "fake_token"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"children": []}}

        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_response

        source = self._make_source()
        fetch_subreddit_posts(
            source, client, "brdev", sort="top", time_filter="month"
        )

        call_args = client.get.call_args
        url = call_args[0][0]
        # Should be /r/brdev/top?t=month&limit=25
        assert "/top" in url
        assert "t=month" in url
