"""Tests for ABStartups StartupBase collector."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.abstartups import (
    ABStartupsCompany,
    fetch_abstartups,
    fetch_all_abstartups,
)


def _source() -> DataSourceConfig:
    return DataSourceConfig(
        name="abstartups",
        source_type="api",
        url="https://startupbase.com.br/api/v1/startups",
    )


def _mock_client(response_data, status_code=200, side_effect=None):
    """Create a mock httpx.Client with a mocked get() method."""
    client = MagicMock(spec=httpx.Client)
    if side_effect:
        client.get.side_effect = side_effect
    else:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=mock_response
            )
        client.get.return_value = mock_response
    return client


class TestFetchAbstartups:
    def test_parses_valid_response(self):
        data = {
            "results": [
                {"name": "Nubank", "slug": "nubank", "sector": "Fintech", "city": "São Paulo", "website": "https://nubank.com.br"},
                {"name": "iFood", "slug": "ifood", "sector": "FoodTech", "city": "Campinas"},
            ]
        }
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)

        assert len(result) == 2
        assert result[0].name == "Nubank"
        assert result[0].slug == "nubank"
        assert result[0].sector == "Fintech"
        assert result[0].city == "São Paulo"
        assert result[0].website == "https://nubank.com.br"

    def test_skips_entries_without_name(self):
        data = {"results": [{"slug": "no-name"}, {"name": "Valid", "slug": "valid"}]}
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)

        assert len(result) == 1
        assert result[0].name == "Valid"

    def test_handles_timeout(self):
        client = _mock_client(None, side_effect=httpx.TimeoutException("timeout"))
        result = fetch_abstartups(_source(), client)
        assert result == []

    def test_handles_empty_response(self):
        data = {"results": []}
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)
        assert result == []

    def test_generates_source_url(self):
        data = {"results": [{"name": "Test Co", "slug": "test-co"}]}
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)
        assert result[0].source_url == "https://startupbase.com.br/startup/test-co"

    def test_handles_list_response_format(self):
        """API might return a raw list instead of paginated envelope."""
        data = [{"name": "Direct List Co", "slug": "direct"}]
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)
        assert len(result) == 1
        assert result[0].name == "Direct List Co"

    def test_generates_slug_from_name_if_missing(self):
        data = {"results": [{"name": "My Cool Startup"}]}
        client = _mock_client(data)
        result = fetch_abstartups(_source(), client)
        assert result[0].slug == "my-cool-startup"

    def test_handles_http_error(self):
        client = _mock_client(None, status_code=500)
        result = fetch_abstartups(_source(), client)
        assert result == []


class TestFetchAllAbstartups:
    def test_stops_on_empty_page(self):
        page1 = [{"name": f"Co {i}", "slug": f"co-{i}"} for i in range(50)]

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.raise_for_status.return_value = None
            if call_count == 1:
                mock_resp.json.return_value = {"results": page1}
            else:
                mock_resp.json.return_value = {"results": []}
            return mock_resp

        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = mock_get

        result = fetch_all_abstartups(_source(), client, max_pages=5, per_page=50)
        assert len(result) == 50

    def test_stops_on_partial_page(self):
        page1 = [{"name": f"Co {i}", "slug": f"co-{i}"} for i in range(30)]
        client = _mock_client({"results": page1})

        result = fetch_all_abstartups(_source(), client, max_pages=5, per_page=50)
        assert len(result) == 30
