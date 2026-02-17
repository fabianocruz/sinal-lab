"""Tests for RADAR collector module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone

from apps.agents.radar.collector import TrendSignal


class TestTrendSignal:
    """Test TrendSignal dataclass."""

    def test_create_signal(self):
        signal = TrendSignal(
            title="Show HN: New AI Framework",
            url="https://news.ycombinator.com/item?id=12345",
            source_name="hn_best",
            source_type="hn",
        )
        assert signal.title == "Show HN: New AI Framework"
        assert signal.source_type == "hn"
        assert signal.content_hash != ""

    def test_content_hash_deduplication(self):
        s1 = TrendSignal(title="A", url="https://x.com/1", source_name="a", source_type="hn")
        s2 = TrendSignal(title="B", url="https://x.com/1", source_name="b", source_type="github")
        s3 = TrendSignal(title="A", url="https://x.com/2", source_name="a", source_type="hn")

        assert s1.content_hash == s2.content_hash  # Same URL
        assert s1.content_hash != s3.content_hash  # Different URL

    def test_default_values(self):
        signal = TrendSignal(title="T", url="https://x.com", source_name="s", source_type="hn")
        assert signal.published_at is None
        assert signal.summary is None
        assert signal.tags == []
        assert signal.metrics == {}

    def test_full_signal(self):
        now = datetime.now(timezone.utc)
        signal = TrendSignal(
            title="langchain/langchain — Framework for LLM apps",
            url="https://github.com/langchain/langchain",
            source_name="github_trending_daily",
            source_type="github",
            published_at=now,
            summary="Build context-aware reasoning applications",
            author="langchain",
            tags=["python", "ai"],
            metrics={"stars": 75000, "forks": 11000, "language": "Python"},
        )
        assert signal.metrics["stars"] == 75000
        assert len(signal.tags) == 2

    def test_metrics_dict(self):
        signal = TrendSignal(
            title="T",
            url="https://x.com",
            source_name="s",
            source_type="github",
            metrics={"stars": 100, "forks": 10},
        )
        assert signal.metrics["stars"] == 100
        assert signal.metrics["forks"] == 10


class TestCollectGitHubTrending:
    """Test GitHub trending repository collection."""

    def test_collect_github_trending_with_none_description(self):
        """Test that repos with None description don't cause NoneType errors.

        Regression test for bug fix on line 181 of collector.py where
        repo.get('description') could return None, causing a TypeError when
        attempting to slice it with [:200].
        """
        from unittest.mock import Mock
        from apps.agents.radar.collector import (
            collect_github_trending,
            DataSourceConfig,
        )

        # Mock data source configuration
        mock_source = Mock(spec=DataSourceConfig)
        mock_source.name = "github_trending_daily"
        mock_source.url = "https://api.github.com/search/repositories"
        mock_source.params = {"window": "daily"}

        # Mock HTTP client with response containing repo with None description
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "user/repo-with-none-description",
                    "html_url": "https://github.com/user/repo-with-none-description",
                    "description": None,  # This is the critical test case
                    "created_at": "2026-02-01T00:00:00Z",
                    "owner": {"login": "user"},
                    "language": "Python",
                    "stargazers_count": 150,
                    "forks_count": 25,
                    "open_issues_count": 5,
                },
                {
                    "full_name": "user/repo-with-description",
                    "html_url": "https://github.com/user/repo-with-description",
                    "description": "A valid description",
                    "created_at": "2026-02-01T00:00:00Z",
                    "owner": {"login": "user"},
                    "language": "JavaScript",
                    "stargazers_count": 200,
                    "forks_count": 30,
                    "open_issues_count": 10,
                },
            ]
        }
        mock_client.get.return_value = mock_response

        # Execute collection - should NOT raise TypeError
        signals = collect_github_trending(mock_source, mock_client)

        # Verify results
        assert len(signals) == 2

        # First repo (None description) should have empty description
        assert "user/repo-with-none-description" in signals[0].title
        assert signals[0].summary == ""  # None converted to empty string
        assert signals[0].url == "https://github.com/user/repo-with-none-description"
        assert signals[0].source_type == "github"
        assert signals[0].metrics["stars"] == 150

        # Second repo (valid description) should work normally
        assert "user/repo-with-description" in signals[1].title
        assert "A valid description" in signals[1].title
        assert signals[1].summary == "A valid description"
        assert signals[1].metrics["stars"] == 200

    def test_collect_github_trending_truncates_long_descriptions(self):
        """Test that long descriptions are truncated to 200 characters in title."""
        from unittest.mock import Mock
        from apps.agents.radar.collector import (
            collect_github_trending,
            DataSourceConfig,
        )

        # Mock source
        mock_source = Mock(spec=DataSourceConfig)
        mock_source.name = "github_trending_daily"
        mock_source.url = "https://api.github.com/search/repositories"
        mock_source.params = {"window": "daily"}

        # Long description (250 characters)
        long_desc = "A" * 250

        # Mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "user/long-description-repo",
                    "html_url": "https://github.com/user/long-description-repo",
                    "description": long_desc,
                    "created_at": "2026-02-01T00:00:00Z",
                    "owner": {"login": "user"},
                    "language": "Python",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "open_issues_count": 2,
                }
            ]
        }
        mock_client.get.return_value = mock_response

        # Execute
        signals = collect_github_trending(mock_source, mock_client)

        # Verify truncation
        assert len(signals) == 1
        # Title should contain "user/long-description-repo — " + first 200 chars of description
        assert signals[0].title.startswith("user/long-description-repo — ")
        # Description in title should be truncated to 200 chars
        description_in_title = signals[0].title.split(" — ")[1]
        assert len(description_in_title) == 200
        assert description_in_title == "A" * 200

        # Full description should be in summary (not truncated)
        assert signals[0].summary == long_desc
        assert len(signals[0].summary) == 250

    def test_collect_github_trending_empty_description(self):
        """Test that repos with empty string description are handled correctly."""
        from unittest.mock import Mock
        from apps.agents.radar.collector import (
            collect_github_trending,
            DataSourceConfig,
        )

        # Mock source
        mock_source = Mock(spec=DataSourceConfig)
        mock_source.name = "github_trending_daily"
        mock_source.url = "https://api.github.com/search/repositories"
        mock_source.params = {"window": "daily"}

        # Mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "user/empty-description",
                    "html_url": "https://github.com/user/empty-description",
                    "description": "",  # Empty string
                    "created_at": "2026-02-01T00:00:00Z",
                    "owner": {"login": "user"},
                    "language": None,
                    "stargazers_count": 50,
                    "forks_count": 5,
                    "open_issues_count": 1,
                }
            ]
        }
        mock_client.get.return_value = mock_response

        # Execute
        signals = collect_github_trending(mock_source, mock_client)

        # Verify
        assert len(signals) == 1
        assert signals[0].title == "user/empty-description — "
        assert signals[0].summary == ""
        assert signals[0].tags == []  # No language tag
