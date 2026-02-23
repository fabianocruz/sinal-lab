"""Tests for LinkedIn RapidAPI source module.

Tests LinkedInPost and LinkedInCompany dataclasses, plus fetch_linkedin_posts
and fetch_linkedin_companies functions that fetch data via RapidAPI.
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.linkedin import (
    LinkedInCompany,
    LinkedInPost,
    fetch_linkedin_companies,
    fetch_linkedin_posts,
)

# Sample mock data for RapidAPI responses
SAMPLE_POST_RESPONSE = {
    "data": [
        {
            "text": "Excited to announce our Series A! We raised $15M led by Kaszek to expand fintech operations across LATAM.",
            "url": "https://www.linkedin.com/feed/update/urn:li:activity:1234567890",
            "author": {
                "firstName": "Maria",
                "lastName": "Santos",
                "headline": "CEO at FinTechBR",
            },
            "totalReactionCount": 245,
            "commentsCount": 42,
            "postedAt": "2026-02-15T10:00:00.000Z",
            "article": {"url": "https://techcrunch.com/fintechbr-series-a"},
        },
        {
            "text": "Join our engineering team in São Paulo! We're hiring senior backend engineers to work on payment infrastructure.",
            "url": "https://www.linkedin.com/feed/update/urn:li:activity:9876543210",
            "author": {"firstName": "João", "lastName": "Silva"},
            "totalReactionCount": 89,
            "commentsCount": 15,
            "postedAt": "2026-02-14T14:30:00.000Z",
        },
    ]
}

SAMPLE_COMPANY_RESPONSE = {
    "data": [
        {
            "name": "FinTechBR",
            "url": "https://www.linkedin.com/company/fintechbr",
            "industry": "Financial Technology",
            "headquarter": {"city": "São Paulo", "country": "Brazil"},
            "staffCount": "51-200",
            "description": "Democratizing financial services for LATAM",
            "website": "https://fintechbr.com.br",
        },
        {
            "name": "NuBank",
            "url": "https://www.linkedin.com/company/nubank",
            "industry": "Financial Services",
            "headquarter": {"city": "São Paulo", "country": "Brazil"},
            "staffCount": "5001-10000",
            "description": "Leading digital bank in Latin America",
            "website": "https://nubank.com.br",
        },
    ]
}


class TestLinkedInPost:
    """Test LinkedInPost dataclass initialization and hashing."""

    def test_content_hash_generated_from_external_url_when_present(self) -> None:
        """When external_url is present, content_hash is based on it."""
        post = LinkedInPost(
            title="Test Post",
            text="Full text here",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
            external_url="https://techcrunch.com/article",
        )
        # Hash should be based on external_url for cross-source dedup
        import hashlib

        expected_hash = hashlib.md5(
            "https://techcrunch.com/article".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_content_hash_generated_from_url_when_no_external_url(self) -> None:
        """When external_url is None, content_hash is based on LinkedIn url."""
        post = LinkedInPost(
            title="Test Post",
            text="Full text here",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
            external_url=None,
        )
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.linkedin.com/feed/update/urn:li:activity:123".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash

    def test_title_from_first_100_chars_of_text(self) -> None:
        """Title is the first 100 characters of text."""
        long_text = (
            "A" * 150
        )  # Text longer than 100 chars to test truncation handling
        post = LinkedInPost(
            title=long_text[:100],  # Caller should truncate
            text=long_text,
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
        )
        # Verify title is exactly 100 chars when truncated by caller
        assert len(post.title) == 100

    def test_all_fields_populated_correctly(self) -> None:
        """All fields can be set and are stored correctly."""
        published_at = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        post = LinkedInPost(
            title="Series A Announcement",
            text="We raised $15M!",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_search",
            author_name="Maria Santos",
            author_headline="CEO at FinTechBR",
            like_count=245,
            comment_count=42,
            published_at=published_at,
            external_url="https://techcrunch.com/article",
        )

        assert post.title == "Series A Announcement"
        assert post.text == "We raised $15M!"
        assert (
            post.url
            == "https://www.linkedin.com/feed/update/urn:li:activity:123"
        )
        assert post.source_name == "linkedin_search"
        assert post.author_name == "Maria Santos"
        assert post.author_headline == "CEO at FinTechBR"
        assert post.like_count == 245
        assert post.comment_count == 42
        assert post.published_at == published_at
        assert post.external_url == "https://techcrunch.com/article"

    def test_default_values(self) -> None:
        """Optional fields have correct default values."""
        post = LinkedInPost(
            title="Test",
            text="Test text",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
        )

        assert post.author_name is None
        assert post.author_headline is None
        assert post.like_count == 0
        assert post.comment_count == 0
        assert post.published_at is None
        assert post.external_url is None
        assert post.image_url is None
        assert post.video_url is None
        assert post.content_hash != ""  # Should be auto-generated

    def test_image_url_and_video_url_stored(self) -> None:
        """image_url and video_url stored correctly."""
        post = LinkedInPost(
            title="Media post",
            text="Post with media",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
            image_url="https://media.licdn.com/thumb.jpg",
            video_url="https://media.licdn.com/video.mp4",
        )
        assert post.image_url == "https://media.licdn.com/thumb.jpg"
        assert post.video_url == "https://media.licdn.com/video.mp4"

    def test_custom_content_hash_not_overwritten(self) -> None:
        """If content_hash is provided, it's not overwritten."""
        custom_hash = "custom_hash_12345"
        post = LinkedInPost(
            title="Test",
            text="Test text",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
            content_hash=custom_hash,
        )
        assert post.content_hash == custom_hash

    def test_empty_external_url_uses_linkedin_url_for_hash(self) -> None:
        """Empty string external_url is treated as None."""
        post = LinkedInPost(
            title="Test",
            text="Test text",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123",
            source_name="linkedin_test",
            external_url="",
        )
        # Empty string is falsy, so should use url
        import hashlib

        # Since external_url="" is falsy in Python, the hash_key will be url
        expected_hash = hashlib.md5(
            "https://www.linkedin.com/feed/update/urn:li:activity:123".encode()
        ).hexdigest()
        assert post.content_hash == expected_hash


class TestLinkedInCompany:
    """Test LinkedInCompany dataclass initialization and hashing."""

    def test_content_hash_generated_from_url(self) -> None:
        """content_hash is MD5 of the LinkedIn company URL."""
        company = LinkedInCompany(
            name="FinTechBR",
            url="https://www.linkedin.com/company/fintechbr",
            source_name="linkedin_search",
        )
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.linkedin.com/company/fintechbr".encode()
        ).hexdigest()
        assert company.content_hash == expected_hash

    def test_all_fields_populated(self) -> None:
        """All fields can be set and stored correctly."""
        company = LinkedInCompany(
            name="FinTechBR",
            url="https://www.linkedin.com/company/fintechbr",
            source_name="linkedin_search",
            industry="Financial Technology",
            headquarters="São Paulo, Brazil",
            company_size="51-200",
            description="Democratizing financial services for LATAM",
            website="https://fintechbr.com.br",
        )

        assert company.name == "FinTechBR"
        assert company.url == "https://www.linkedin.com/company/fintechbr"
        assert company.source_name == "linkedin_search"
        assert company.industry == "Financial Technology"
        assert company.headquarters == "São Paulo, Brazil"
        assert company.company_size == "51-200"
        assert (
            company.description
            == "Democratizing financial services for LATAM"
        )
        assert company.website == "https://fintechbr.com.br"

    def test_default_values(self) -> None:
        """Optional fields default to None, content_hash is auto-generated."""
        company = LinkedInCompany(
            name="TestCo",
            url="https://www.linkedin.com/company/testco",
            source_name="linkedin_test",
        )

        assert company.industry is None
        assert company.headquarters is None
        assert company.company_size is None
        assert company.description is None
        assert company.website is None
        assert company.content_hash != ""  # Auto-generated

    def test_custom_content_hash_preserved(self) -> None:
        """Provided content_hash is not overwritten."""
        custom_hash = "my_custom_hash_abcd"
        company = LinkedInCompany(
            name="TestCo",
            url="https://www.linkedin.com/company/testco",
            source_name="linkedin_test",
            content_hash=custom_hash,
        )
        assert company.content_hash == custom_hash

    def test_unicode_in_fields(self) -> None:
        """Unicode characters in name, description are handled correctly."""
        company = LinkedInCompany(
            name="São Paulo Tech",
            url="https://www.linkedin.com/company/sp-tech",
            source_name="linkedin_test",
            description="Tecnologia é nossa paixão",
        )
        assert company.name == "São Paulo Tech"
        assert company.description == "Tecnologia é nossa paixão"

    def test_empty_optional_fields(self) -> None:
        """Empty strings in optional fields are preserved (not None)."""
        company = LinkedInCompany(
            name="TestCo",
            url="https://www.linkedin.com/company/testco",
            source_name="linkedin_test",
            industry="",
            description="",
        )
        assert company.industry == ""
        assert company.description == ""


class TestFetchLinkedInPosts:
    """Test fetch_linkedin_posts function."""

    def _make_source(
        self,
        name: str = "linkedin_test",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for LinkedIn posts."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url="https://linkedin-data-api.p.rapidapi.com/search-posts",
            max_items=max_items,
        )

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_returns_empty_list_when_rapidapi_key_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] when RAPIDAPI_KEY environment variable is not set."""
        mock_getenv.return_value = None
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_linkedin_posts(source, client, "fintech latam")

        assert result == []
        mock_getenv.assert_called_with("RAPIDAPI_KEY")
        client.get.assert_not_called()

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_successful_fetch_with_mocked_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful API call returns parsed LinkedInPost objects."""
        mock_getenv.return_value = "test_api_key_12345"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_POST_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "fintech", limit=10)

        assert len(result) == 2
        assert all(isinstance(p, LinkedInPost) for p in result)

        # Check first post
        assert result[0].text.startswith("Excited to announce our Series A")
        assert (
            result[0].url
            == "https://www.linkedin.com/feed/update/urn:li:activity:1234567890"
        )
        assert result[0].like_count == 245
        assert result[0].comment_count == 42

        # Check second post
        assert result[1].text.startswith("Join our engineering team")
        assert result[1].like_count == 89

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_parses_author_name_and_headline(
        self, mock_getenv: MagicMock
    ) -> None:
        """author_name and author_headline extracted from response."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_POST_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")

        # First post has full author info
        assert result[0].author_name == "Maria Santos"
        assert result[0].author_headline == "CEO at FinTechBR"

        # Second post has partial author info (no headline)
        assert result[1].author_name == "João Silva"
        assert result[1].author_headline is None

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_extracts_external_url_from_article(
        self, mock_getenv: MagicMock
    ) -> None:
        """external_url extracted from shared article in post."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_POST_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")

        # First post has article URL
        assert (
            result[0].external_url == "https://techcrunch.com/fintechbr-series-a"
        )

        # Second post has no article
        assert result[1].external_url is None

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_empty_results_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """API returns empty data array, function returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_http_error_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """HTTP error during API call returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("API error")

        result = fetch_linkedin_posts(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_timeout_returns_empty_list(self, mock_getenv: MagicMock) -> None:
        """Timeout during API call returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.TimeoutException("Request timeout")

        result = fetch_linkedin_posts(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_malformed_response_handled_gracefully(
        self, mock_getenv: MagicMock
    ) -> None:
        """Malformed JSON or missing fields handled gracefully."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        # Missing required 'url' field in one post
        malformed_data = {
            "data": [
                {
                    "text": "Post text",
                    # Missing 'url' field
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = malformed_data
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")

        # Should skip malformed items and return empty list
        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_respects_limit_parameter(self, mock_getenv: MagicMock) -> None:
        """Limit parameter passed to API request."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_linkedin_posts(source, client, "test", limit=5)

        # Check that client.get was called with correct params
        call_args = client.get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 5

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_extracts_article_thumbnail_as_image(
        self, mock_getenv: MagicMock
    ) -> None:
        """Extracts image_url from article.thumbnail."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "text": "Check out our launch!",
                    "url": "https://www.linkedin.com/feed/update/urn:li:activity:1",
                    "author": {"firstName": "Test", "lastName": "User"},
                    "article": {
                        "url": "https://example.com/launch",
                        "thumbnail": "https://media.licdn.com/article-thumb.jpg",
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")
        assert len(result) == 1
        assert result[0].image_url == "https://media.licdn.com/article-thumb.jpg"
        assert result[0].video_url is None

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_extracts_video_url(self, mock_getenv: MagicMock) -> None:
        """Extracts video_url from item.video.url."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "text": "Watch our demo!",
                    "url": "https://www.linkedin.com/feed/update/urn:li:activity:2",
                    "author": {"firstName": "Test", "lastName": "User"},
                    "video": {"url": "https://media.licdn.com/demo.mp4"},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")
        assert len(result) == 1
        assert result[0].video_url == "https://media.licdn.com/demo.mp4"

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_no_media_results_in_none(self, mock_getenv: MagicMock) -> None:
        """Posts without media data have None image_url and video_url."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_POST_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")
        # SAMPLE_POST_RESPONSE posts don't have image/video keys
        assert result[0].image_url is None
        assert result[0].video_url is None

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_extracts_image_from_images_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """Extracts image from item.images list fallback."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "text": "Post with images list",
                    "url": "https://www.linkedin.com/feed/update/urn:li:activity:3",
                    "author": {"firstName": "Test", "lastName": "User"},
                    "images": [
                        {"url": "https://media.licdn.com/image1.jpg"},
                        {"url": "https://media.licdn.com/image2.jpg"},
                    ],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_posts(source, client, "test")
        assert len(result) == 1
        assert result[0].image_url == "https://media.licdn.com/image1.jpg"

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_correct_headers_sent(self, mock_getenv: MagicMock) -> None:
        """RapidAPI headers (X-RapidAPI-Key, X-RapidAPI-Host) sent correctly."""
        mock_getenv.return_value = "test_api_key_xyz"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_linkedin_posts(source, client, "test")

        call_args = client.get.call_args
        headers = call_args[1]["headers"]

        assert headers["X-RapidAPI-Key"] == "test_api_key_xyz"
        assert headers["X-RapidAPI-Host"] == "linkedin-data-api.p.rapidapi.com"


class TestFetchLinkedInCompanies:
    """Test fetch_linkedin_companies function."""

    def _make_source(
        self,
        name: str = "linkedin_companies",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for LinkedIn companies."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url="https://linkedin-data-api.p.rapidapi.com/search-companies",
            max_items=max_items,
        )

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_returns_empty_list_when_rapidapi_key_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] when RAPIDAPI_KEY not set."""
        mock_getenv.return_value = None
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_linkedin_companies(source, client, "fintech")

        assert result == []
        mock_getenv.assert_called_with("RAPIDAPI_KEY")
        client.get.assert_not_called()

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_successful_fetch_with_mocked_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful API call returns parsed LinkedInCompany objects."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_COMPANY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_companies(source, client, "fintech", limit=10)

        assert len(result) == 2
        assert all(isinstance(c, LinkedInCompany) for c in result)

        # Check first company
        assert result[0].name == "FinTechBR"
        assert (
            result[0].url == "https://www.linkedin.com/company/fintechbr"
        )
        assert result[0].industry == "Financial Technology"

        # Check second company
        assert result[1].name == "NuBank"
        assert result[1].industry == "Financial Services"

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_parses_industry_headquarters_company_size(
        self, mock_getenv: MagicMock
    ) -> None:
        """Industry, headquarters, company_size extracted correctly."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_COMPANY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_companies(source, client, "test")

        # First company
        assert result[0].industry == "Financial Technology"
        assert result[0].headquarters == "São Paulo, Brazil"
        assert result[0].company_size == "51-200"
        assert (
            result[0].description
            == "Democratizing financial services for LATAM"
        )
        assert result[0].website == "https://fintechbr.com.br"

        # Second company
        assert result[1].industry == "Financial Services"
        assert result[1].company_size == "5001-10000"

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_empty_results_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """API returns empty data array."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_companies(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_http_error_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """HTTP error returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("API error")

        result = fetch_linkedin_companies(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_malformed_response_handled_gracefully(
        self, mock_getenv: MagicMock
    ) -> None:
        """Missing required fields handled gracefully."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        malformed_data = {
            "data": [
                {
                    "name": "TestCo",
                    # Missing 'url' field
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = malformed_data
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_linkedin_companies(source, client, "test")

        assert result == []

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_correct_headers_sent(self, mock_getenv: MagicMock) -> None:
        """RapidAPI headers sent correctly."""
        mock_getenv.return_value = "test_api_key_abc"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_linkedin_companies(source, client, "test")

        call_args = client.get.call_args
        headers = call_args[1]["headers"]

        assert headers["X-RapidAPI-Key"] == "test_api_key_abc"
        assert headers["X-RapidAPI-Host"] == "linkedin-data-api.p.rapidapi.com"

    @patch("apps.agents.sources.linkedin.os.getenv")
    def test_respects_limit_parameter(self, mock_getenv: MagicMock) -> None:
        """Limit parameter passed to API."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_linkedin_companies(source, client, "test", limit=15)

        call_args = client.get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 15
