"""Tests for async GitHub repository fetching.

Async variants of the shared GitHub source module for IO-bound concurrent
API fetching via asyncio.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.async_github import (
    fetch_github_repos_async,
    fetch_github_repos_concurrent,
)
from apps.agents.sources.github import GitHubRepoItem


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


def _make_api_response(count: int = 2) -> dict:
    """Create a mock GitHub search API response with N repos."""
    items = []
    for i in range(count):
        items.append({
            "full_name": "user/repo{}".format(i),
            "html_url": "https://github.com/user/repo{}".format(i),
            "description": "Repo {} description".format(i),
            "language": "Python",
            "stargazers_count": 100 + i,
            "forks_count": 10 + i,
            "open_issues_count": 5,
            "owner": {"login": "user"},
            "created_at": "2026-02-10T12:00:00Z",
        })
    return {"items": items}


@pytest.mark.asyncio
class TestFetchGitHubReposAsync:
    """Test async single GitHub API fetch."""

    async def test_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _make_api_response(2)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        source = _make_source()
        items = await fetch_github_repos_async(source, mock_client)

        assert len(items) == 2
        assert items[0].full_name == "user/repo0"
        assert isinstance(items[0], GitHubRepoItem)

    async def test_http_error_returns_empty(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Rate limited"))

        source = _make_source()
        items = await fetch_github_repos_async(source, mock_client)

        assert items == []

    async def test_no_url_returns_empty(self) -> None:
        source = DataSourceConfig(name="github", source_type="api", url=None)
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        items = await fetch_github_repos_async(source, mock_client)

        assert items == []

    async def test_respects_min_stars(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _make_api_response(0)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        source = _make_source()
        await fetch_github_repos_async(source, mock_client, min_stars=20)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "stars:>20" in params.get("q", "")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token_async"})
    async def test_auth_token_from_env(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _make_api_response(0)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        source = _make_source()
        await fetch_github_repos_async(source, mock_client)

        call_kwargs = mock_client.get.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer test_token_async"


@pytest.mark.asyncio
class TestFetchGitHubReposConcurrent:
    """Test concurrent multi-source GitHub fetching."""

    async def test_multiple_sources(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = _make_api_response(2)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        sources = [
            _make_source("https://api.github.com/search/repositories"),
            _make_source("https://api.github.com/search/repositories"),
        ]

        items = await fetch_github_repos_concurrent(sources, mock_client)

        # 2 sources x 2 repos each = 4
        assert len(items) == 4

    async def test_one_failure_doesnt_block_others(self) -> None:
        good_response = MagicMock()
        good_response.json.return_value = _make_api_response(2)
        good_response.raise_for_status = MagicMock()

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise httpx.HTTPError("Source 2 failed")
            return good_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=side_effect)

        sources = [
            _make_source("https://api.github.com/search/repositories"),
            _make_source("https://api.github.com/search/repositories"),
            _make_source("https://api.github.com/search/repositories"),
        ]

        items = await fetch_github_repos_concurrent(sources, mock_client)

        # 2 successful sources x 2 repos = 4
        assert len(items) == 4

    async def test_empty_sources(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        items = await fetch_github_repos_concurrent([], mock_client)

        assert items == []

    async def test_respects_max_concurrency(self) -> None:
        """Verify that we don't exceed max_concurrency simultaneous requests."""
        concurrent_count = 0
        max_concurrent = 0

        good_response = MagicMock()
        good_response.json.return_value = _make_api_response(1)
        good_response.raise_for_status = MagicMock()

        async def counting_get(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return good_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=counting_get)

        sources = [
            _make_source("https://api.github.com/search/repositories")
            for _ in range(10)
        ]

        items = await fetch_github_repos_concurrent(
            sources, mock_client, max_concurrency=3
        )

        assert max_concurrent <= 3
        assert len(items) == 10  # 10 sources x 1 repo each
