"""Tests for ProductHunt GraphQL source module.

Tests ProductHuntPost dataclass and fetch_producthunt_posts function that
fetches data from the ProductHunt GraphQL API with dev token authentication.
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.producthunt import (
    PRODUCTHUNT_API_URL,
    ProductHuntPost,
    fetch_producthunt_posts,
)

# Sample mock data for GraphQL API response
SAMPLE_GRAPHQL_RESPONSE = {
    "data": {
        "posts": {
            "edges": [
                {
                    "node": {
                        "id": "123456",
                        "name": "DevToolX",
                        "tagline": "AI-powered code review for LATAM teams",
                        "url": "https://www.producthunt.com/posts/devtoolx",
                        "website": "https://devtoolx.com",
                        "description": "DevToolX helps engineering teams in Latin America ship better code with AI-powered reviews",
                        "votesCount": 342,
                        "commentsCount": 28,
                        "createdAt": "2026-02-15T10:00:00Z",
                        "topics": {
                            "edges": [
                                {"node": {"name": "Developer Tools"}},
                                {"node": {"name": "Artificial Intelligence"}},
                            ]
                        },
                        "makers": [
                            {"name": "Carlos Silva"},
                            {"name": "Ana Costa"},
                        ],
                        "thumbnail": {
                            "url": "https://ph-files.imgix.net/devtoolx.png"
                        },
                    }
                },
                {
                    "node": {
                        "id": "789012",
                        "name": "FinTrack",
                        "tagline": "Open-source fintech analytics",
                        "url": "https://www.producthunt.com/posts/fintrack",
                        "website": "https://fintrack.io",
                        "description": None,
                        "votesCount": 156,
                        "commentsCount": 12,
                        "createdAt": "2026-02-14T08:30:00Z",
                        "topics": {"edges": [{"node": {"name": "Fintech"}}]},
                        "makers": [],
                        "thumbnail": None,
                    }
                },
            ]
        }
    }
}


class TestProductHuntPost:
    """Test ProductHuntPost dataclass initialization and content hashing."""

    def test_content_hash_from_website_when_present(self) -> None:
        """content_hash generated from website URL for cross-source dedup."""
        post = ProductHuntPost(
            name="DevToolX",
            tagline="AI-powered code review",
            url="https://www.producthunt.com/posts/devtoolx",
            source_name="ph_test",
            website="https://devtoolx.com",
        )
        # Hash should be MD5 of website URL for cross-source deduplication
        import hashlib

        expected_hash = hashlib.md5("https://devtoolx.com".encode()).hexdigest()
        assert post.content_hash == expected_hash

    def test_content_hash_from_url_when_no_website(self) -> None:
        """content_hash generated from ProductHunt URL when no website."""
        post = ProductHuntPost(
            name="DevToolX",
            tagline="AI-powered code review",
            url="https://www.producthunt.com/posts/devtoolx",
            source_name="ph_test",
            website=None,
        )
        # Hash should be MD5 of ProductHunt URL
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.producthunt.com/posts/devtoolx".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_all_fields_populated_correctly(self) -> None:
        """All fields can be set and stored correctly."""
        created_at = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        post = ProductHuntPost(
            name="DevToolX",
            tagline="AI-powered code review for LATAM teams",
            url="https://www.producthunt.com/posts/devtoolx",
            source_name="ph_latam",
            website="https://devtoolx.com",
            description="DevToolX helps engineering teams ship better code",
            votes_count=342,
            comments_count=28,
            created_at=created_at,
            topics=["Developer Tools", "Artificial Intelligence"],
            makers=["Carlos Silva", "Ana Costa"],
            thumbnail_url="https://ph-files.imgix.net/devtoolx.png",
        )

        assert post.name == "DevToolX"
        assert post.tagline == "AI-powered code review for LATAM teams"
        assert post.url == "https://www.producthunt.com/posts/devtoolx"
        assert post.source_name == "ph_latam"
        assert post.website == "https://devtoolx.com"
        assert post.description == "DevToolX helps engineering teams ship better code"
        assert post.votes_count == 342
        assert post.comments_count == 28
        assert post.created_at == created_at
        assert post.topics == ["Developer Tools", "Artificial Intelligence"]
        assert post.makers == ["Carlos Silva", "Ana Costa"]
        assert post.thumbnail_url == "https://ph-files.imgix.net/devtoolx.png"

    def test_default_values(self) -> None:
        """Optional fields have correct default values."""
        post = ProductHuntPost(
            name="TestProduct",
            tagline="Test tagline",
            url="https://www.producthunt.com/posts/test",
            source_name="ph_test",
        )

        assert post.website is None
        assert post.description is None
        assert post.votes_count == 0
        assert post.comments_count == 0
        assert post.created_at is None
        assert post.topics == []
        assert post.makers == []
        assert post.thumbnail_url is None
        assert post.content_hash != ""  # Should be auto-generated

    def test_custom_content_hash_not_overwritten(self) -> None:
        """If content_hash is provided, it's not overwritten."""
        custom_hash = "custom_hash_xyz123"
        post = ProductHuntPost(
            name="TestProduct",
            tagline="Test tagline",
            url="https://www.producthunt.com/posts/test",
            source_name="ph_test",
            content_hash=custom_hash,
        )
        assert post.content_hash == custom_hash

    def test_empty_website_treated_as_falsy(self) -> None:
        """Empty string website is treated as falsy, falls back to url."""
        post = ProductHuntPost(
            name="TestProduct",
            tagline="Test tagline",
            url="https://www.producthunt.com/posts/test",
            source_name="ph_test",
            website="",
        )
        # Empty string is falsy, should use url for hash
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.producthunt.com/posts/test".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_topics_list_populated(self) -> None:
        """Topics list can be populated and retrieved."""
        post = ProductHuntPost(
            name="TestProduct",
            tagline="Test tagline",
            url="https://www.producthunt.com/posts/test",
            source_name="ph_test",
            topics=["Fintech", "SaaS", "Productivity"],
        )
        assert len(post.topics) == 3
        assert "Fintech" in post.topics
        assert "SaaS" in post.topics
        assert "Productivity" in post.topics

    def test_makers_list_populated(self) -> None:
        """Makers list can be populated and retrieved."""
        post = ProductHuntPost(
            name="TestProduct",
            tagline="Test tagline",
            url="https://www.producthunt.com/posts/test",
            source_name="ph_test",
            makers=["Maria Santos", "João Silva", "Ana Costa"],
        )
        assert len(post.makers) == 3
        assert "Maria Santos" in post.makers
        assert "João Silva" in post.makers
        assert "Ana Costa" in post.makers


class TestFetchProductHuntPosts:
    """Test fetch_producthunt_posts function."""

    def _make_source(
        self,
        name: str = "ph_test",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for ProductHunt."""
        return DataSourceConfig(
            name=name,
            source_type="graphql",
            url=PRODUCTHUNT_API_URL,
            max_items=max_items,
            params={},
        )

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_returns_empty_list_when_token_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] when PRODUCTHUNT_TOKEN environment variable is not set."""
        mock_getenv.return_value = None
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_producthunt_posts(source, client)

        assert result == []
        mock_getenv.assert_called_with("PRODUCTHUNT_TOKEN")
        client.post.assert_not_called()

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_successful_fetch_with_mocked_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful GraphQL call returns parsed ProductHuntPost objects."""
        mock_getenv.return_value = "test_token_12345"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        assert len(result) == 2
        assert all(isinstance(p, ProductHuntPost) for p in result)

        # Check first post
        assert result[0].name == "DevToolX"
        assert result[0].tagline == "AI-powered code review for LATAM teams"
        assert result[0].url == "https://www.producthunt.com/posts/devtoolx"
        assert result[0].website == "https://devtoolx.com"
        assert result[0].votes_count == 342
        assert result[0].comments_count == 28

        # Check second post
        assert result[1].name == "FinTrack"
        assert result[1].tagline == "Open-source fintech analytics"
        assert result[1].votes_count == 156

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_parses_name_tagline_url_website_correctly(
        self, mock_getenv: MagicMock
    ) -> None:
        """name, tagline, url, and website extracted from response."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        # First post
        assert result[0].name == "DevToolX"
        assert result[0].tagline == "AI-powered code review for LATAM teams"
        assert result[0].url == "https://www.producthunt.com/posts/devtoolx"
        assert result[0].website == "https://devtoolx.com"

        # Second post
        assert result[1].name == "FinTrack"
        assert result[1].url == "https://www.producthunt.com/posts/fintrack"
        assert result[1].website == "https://fintrack.io"

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_parses_votes_count_and_comments_count(
        self, mock_getenv: MagicMock
    ) -> None:
        """votes_count and comments_count extracted correctly."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        assert result[0].votes_count == 342
        assert result[0].comments_count == 28
        assert result[1].votes_count == 156
        assert result[1].comments_count == 12

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_parses_created_at_timestamp(self, mock_getenv: MagicMock) -> None:
        """created_at timestamp parsed correctly."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        assert result[0].created_at == datetime(
            2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc
        )
        assert result[1].created_at == datetime(
            2026, 2, 14, 8, 30, 0, tzinfo=timezone.utc
        )

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_extracts_topics_from_response(self, mock_getenv: MagicMock) -> None:
        """Topics extracted from nested edges/node structure."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        # First post has 2 topics
        assert len(result[0].topics) == 2
        assert "Developer Tools" in result[0].topics
        assert "Artificial Intelligence" in result[0].topics

        # Second post has 1 topic
        assert len(result[1].topics) == 1
        assert "Fintech" in result[1].topics

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_extracts_makers_from_response(self, mock_getenv: MagicMock) -> None:
        """Makers extracted from response."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GRAPHQL_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        # First post has 2 makers
        assert len(result[0].makers) == 2
        assert "Carlos Silva" in result[0].makers
        assert "Ana Costa" in result[0].makers

        # Second post has no makers
        assert len(result[1].makers) == 0

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_empty_results_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """Empty results returns empty list."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        empty_response = {"data": {"posts": {"edges": []}}}
        mock_response = MagicMock()
        mock_response.json.return_value = empty_response
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        assert result == []

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_http_error_returns_empty_list(self, mock_getenv: MagicMock) -> None:
        """HTTP error during API call returns []."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.post.side_effect = httpx.HTTPError("API error")

        result = fetch_producthunt_posts(source, client)

        assert result == []

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_timeout_returns_empty_list(self, mock_getenv: MagicMock) -> None:
        """Timeout during API call returns []."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.post.side_effect = httpx.TimeoutException("Request timeout")

        result = fetch_producthunt_posts(source, client)

        assert result == []

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_malformed_response_handled_gracefully(
        self, mock_getenv: MagicMock
    ) -> None:
        """Malformed response handled gracefully."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        # Missing required 'name' field in one post
        malformed_response = {
            "data": {
                "posts": {
                    "edges": [
                        {
                            "node": {
                                # Missing 'name' field
                                "tagline": "Test tagline",
                                "url": "https://www.producthunt.com/posts/test",
                            }
                        }
                    ]
                }
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = malformed_response
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        result = fetch_producthunt_posts(source, client)

        # Should skip malformed items and return empty list
        assert result == []

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_correct_headers_sent(self, mock_getenv: MagicMock) -> None:
        """Authorization Bearer token and Content-Type headers sent correctly."""
        mock_getenv.return_value = "test_token_xyz789"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"posts": {"edges": []}}}
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        fetch_producthunt_posts(source, client)

        call_args = client.post.call_args
        headers = call_args[1]["headers"]

        assert headers["Authorization"] == "Bearer test_token_xyz789"
        assert headers["Content-Type"] == "application/json"

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_graphql_query_body_well_formed(self, mock_getenv: MagicMock) -> None:
        """GraphQL query body contains posts, limit, and sort parameters."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"posts": {"edges": []}}}
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        fetch_producthunt_posts(source, client)

        call_args = client.post.call_args
        json_body = call_args[1]["json"]

        # Should have 'query' and 'variables' keys
        assert "query" in json_body
        assert "variables" in json_body

        # Query should contain 'posts' keyword
        assert "posts" in json_body["query"]

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_respects_limit_parameter(self, mock_getenv: MagicMock) -> None:
        """Limit parameter passed to GraphQL query."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"posts": {"edges": []}}}
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        fetch_producthunt_posts(source, client, limit=10)

        call_args = client.post.call_args
        json_body = call_args[1]["json"]
        variables = json_body.get("variables", {})

        # Should have limit in variables
        assert variables.get("limit") == 10

    @patch("apps.agents.sources.producthunt.os.getenv")
    def test_respects_posted_after_parameter(
        self, mock_getenv: MagicMock
    ) -> None:
        """posted_after parameter passed to GraphQL query."""
        mock_getenv.return_value = "test_token"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"posts": {"edges": []}}}
        mock_response.raise_for_status = MagicMock()
        client.post.return_value = mock_response

        fetch_producthunt_posts(source, client, posted_after="2026-02-10")

        call_args = client.post.call_args
        json_body = call_args[1]["json"]
        variables = json_body.get("variables", {})

        # Should have posted_after in variables
        assert variables.get("postedAfter") == "2026-02-10"
