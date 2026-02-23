"""Tests for Y Combinator portfolio collector."""

from unittest.mock import MagicMock

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.yc_portfolio import (
    LATAM_COUNTRIES,
    YCCompany,
    _is_latam_location,
    fetch_yc_companies,
    filter_latam,
)


def _source() -> DataSourceConfig:
    return DataSourceConfig(
        name="yc_portfolio",
        source_type="api",
        url="https://www.ycombinator.com/companies",
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


class TestIsLatamLocation:
    def test_brazil_country(self):
        assert _is_latam_location(country="Brazil") is True

    def test_brasil_country(self):
        assert _is_latam_location(country="Brasil") is True

    def test_mexico_country(self):
        assert _is_latam_location(country="Mexico") is True

    def test_usa_not_latam(self):
        assert _is_latam_location(country="United States") is False

    def test_latam_city_fallback(self):
        assert _is_latam_location(city="São Paulo") is True

    def test_region_latin_america(self):
        assert _is_latam_location(region="Latin America") is True

    def test_empty_not_latam(self):
        assert _is_latam_location() is False

    def test_case_insensitive_country(self):
        assert _is_latam_location(country="brazil") is True

    def test_partial_country_match(self):
        assert _is_latam_location(country="São Paulo, Brazil") is True


class TestFetchYcCompanies:
    def test_parses_valid_response(self):
        data = {
            "companies": [
                {"name": "Neon", "slug": "neon", "batch": "W19", "country": "Brazil", "vertical": "Fintech"},
                {"name": "Rappi", "slug": "rappi", "batch": "S16", "country": "Colombia", "vertical": "Delivery"},
            ]
        }
        client = _mock_client(data)
        result = fetch_yc_companies(_source(), client)

        assert len(result) == 2
        assert result[0].name == "Neon"
        assert result[0].batch == "W19"
        assert result[0].country == "Brazil"

    def test_handles_timeout(self):
        client = _mock_client(None, side_effect=httpx.TimeoutException("timeout"))
        result = fetch_yc_companies(_source(), client)
        assert result == []

    def test_skips_entries_without_name(self):
        data = {"companies": [{"slug": "no-name"}, {"name": "Valid", "slug": "valid"}]}
        client = _mock_client(data)
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1

    def test_generates_source_url(self):
        data = {"companies": [{"name": "Neon", "slug": "neon", "country": "Brazil"}]}
        client = _mock_client(data)
        result = fetch_yc_companies(_source(), client)
        assert result[0].source_url == "https://www.ycombinator.com/companies/neon"

    def test_handles_list_response(self):
        """Some endpoints return a raw list."""
        data = [{"name": "ListCo", "slug": "listco"}]
        client = _mock_client(data)
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1
        assert result[0].name == "ListCo"

    def test_handles_http_error(self):
        client = _mock_client(None, status_code=500)
        result = fetch_yc_companies(_source(), client)
        assert result == []


class TestFilterLatam:
    def test_filters_to_latam_only(self):
        companies = [
            YCCompany(name="Neon", slug="neon", country="Brazil"),
            YCCompany(name="Stripe", slug="stripe", country="United States"),
            YCCompany(name="Rappi", slug="rappi", country="Colombia"),
        ]
        result = filter_latam(companies)
        assert len(result) == 2
        assert {c.name for c in result} == {"Neon", "Rappi"}

    def test_empty_list(self):
        assert filter_latam([]) == []

    def test_no_latam_companies(self):
        companies = [
            YCCompany(name="Stripe", slug="stripe", country="United States"),
            YCCompany(name="Monzo", slug="monzo", country="United Kingdom"),
        ]
        result = filter_latam(companies)
        assert result == []

    def test_city_based_detection(self):
        companies = [
            YCCompany(name="SomeCo", slug="someco", city="São Paulo"),
        ]
        result = filter_latam(companies)
        assert len(result) == 1
