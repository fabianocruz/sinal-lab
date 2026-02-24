"""Tests for shared GitHub collector.

Tests fetch_github_repos and GitHubRepoItem, replacing duplicated
GitHub API code in radar and codigo collectors.
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.agents.sources.github import GitHubRepoItem, fetch_github_repos
from apps.agents.base.config import DataSourceConfig


def _make_source(
    url: str = "https://api.github.com/search/repositories",
    **params: object,
) -> DataSourceConfig:
    return DataSourceConfig(
        name="github_trending",
        source_type="api",
        url=url,
        params=dict(params) if params else {},
    )


def _make_repo_json(
    full_name: str = "owner/repo",
    html_url: str = "https://github.com/owner/repo",
    description: str = "A test repo",
    language: str = "Python",
    stars: int = 100,
    forks: int = 10,
    created_at: str = "2026-02-10T12:00:00Z",
) -> dict:
    return {
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "language": language,
        "stargazers_count": stars,
        "forks_count": forks,
        "open_issues_count": 5,
        "owner": {"login": "owner"},
        "created_at": created_at,
    }


class TestFetchGitHubRepos:
    """Test fetch_github_repos HTTP fetching + JSON parsing."""

    def test_success_with_items(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                _make_repo_json("user/repo1", stars=200),
                _make_repo_json("user/repo2", stars=150),
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        items = fetch_github_repos(source, mock_client)
        assert len(items) == 2
        assert items[0].full_name == "user/repo1"
        assert items[0].stars == 200
        assert items[1].full_name == "user/repo2"

    def test_empty_results(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        items = fetch_github_repos(source, mock_client)
        assert items == []

    def test_http_error_returns_empty(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.HTTPError("Rate limited")

        source = _make_source()
        items = fetch_github_repos(source, mock_client)
        assert items == []

    def test_no_url_returns_empty(self) -> None:
        source = DataSourceConfig(name="github_trending", source_type="api", url=None)
        mock_client = MagicMock(spec=httpx.Client)
        items = fetch_github_repos(source, mock_client)
        assert items == []

    def test_respects_min_stars_param(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        fetch_github_repos(source, mock_client, min_stars=20)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        assert "stars:>20" in params.get("q", "")

    def test_daily_window(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        fetch_github_repos(source, mock_client, window="daily")

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        assert "created:>" in params.get("q", "")

    def test_weekly_window(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source(window="weekly")
        fetch_github_repos(source, mock_client, window="weekly")

        # Just verify it doesn't crash with weekly window
        mock_client.get.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token_123"})
    def test_auth_token_from_env(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        fetch_github_repos(source, mock_client)

        call_kwargs = mock_client.get.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        assert headers.get("Authorization") == "Bearer test_token_123"

    def test_missing_created_at_handled(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "user/repo",
                    "html_url": "https://github.com/user/repo",
                    "description": "No date",
                    "language": "Python",
                    "stargazers_count": 50,
                    "forks_count": 5,
                    "open_issues_count": 1,
                    "owner": {"login": "user"},
                    # No created_at field
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()
        items = fetch_github_repos(source, mock_client)
        assert len(items) == 1
        assert items[0].created_at is None


class TestGitHubRepoItem:
    """Test GitHubRepoItem dataclass."""

    def test_auto_content_hash(self) -> None:
        item = GitHubRepoItem(
            full_name="user/repo",
            url="https://github.com/user/repo",
            description="Test",
            source_name="github",
        )
        assert item.content_hash
        assert len(item.content_hash) == 32

    def test_preserves_manual_hash(self) -> None:
        item = GitHubRepoItem(
            full_name="user/repo",
            url="https://github.com/user/repo",
            description="Test",
            source_name="github",
            content_hash="manual_hash",
        )
        assert item.content_hash == "manual_hash"


class TestTopicFilter:
    """Test optional topic-filtered queries via source.params['topics']."""

    def test_topic_qualifiers_appended(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source(topics="fintech,stablecoin,defi")
        fetch_github_repos(source, mock_client)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        q = params.get("q", "")
        assert "topic:fintech" in q
        assert "topic:stablecoin" in q
        assert "topic:defi" in q

    def test_no_topics_param_backward_compat(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source()  # No topics param
        fetch_github_repos(source, mock_client)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        q = params.get("q", "")
        assert "topic:" not in q

    def test_empty_topics_ignored(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source(topics="")
        fetch_github_repos(source, mock_client)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        q = params.get("q", "")
        assert "topic:" not in q

    def test_whitespace_topics_trimmed(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        source = _make_source(topics=" fintech , , defi ")
        fetch_github_repos(source, mock_client)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
        q = params.get("q", "")
        assert "topic:fintech" in q
        assert "topic:defi" in q
        # Empty entries between commas should be skipped
        assert "topic: " not in q
        assert "topic:," not in q
