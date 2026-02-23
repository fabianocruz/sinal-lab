"""Tests for Y Combinator portfolio collector (Algolia + legacy)."""

from unittest.mock import MagicMock, call

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.yc_portfolio import (
    LATAM_CITIES,
    LATAM_COUNTRIES,
    YCCompany,
    _hit_to_company,
    _is_latam_location,
    _parse_location,
    fetch_yc_companies,
    filter_latam,
)


def _source() -> DataSourceConfig:
    return DataSourceConfig(
        name="yc_portfolio",
        source_type="api",
        url="https://www.ycombinator.com/companies",
    )


def _algolia_response(hits, nb_pages=1, page=0):
    """Build an Algolia-style response dict."""
    return {
        "hits": hits,
        "nbPages": nb_pages,
        "page": page,
        "nbHits": len(hits),
        "hitsPerPage": 1000,
    }


def _algolia_hit(name, slug=None, **kwargs):
    """Build a single Algolia hit dict."""
    hit = {
        "name": name,
        "slug": slug or name.lower().replace(" ", "-"),
    }
    hit.update(kwargs)
    return hit


def _mock_client_algolia(post_responses=None, post_side_effect=None,
                          get_response=None, get_side_effect=None):
    """Create a mock client with separate post (Algolia) and get (legacy) mocking."""
    client = MagicMock(spec=httpx.Client)

    # Mock post() for Algolia
    if post_side_effect:
        client.post.side_effect = post_side_effect
    elif post_responses is not None:
        if isinstance(post_responses, list):
            mock_responses = []
            for resp_data in post_responses:
                mock_resp = MagicMock(spec=httpx.Response)
                mock_resp.status_code = 200
                mock_resp.json.return_value = resp_data
                mock_resp.raise_for_status.return_value = None
                mock_responses.append(mock_resp)
            client.post.side_effect = mock_responses
        else:
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = post_responses
            mock_resp.raise_for_status.return_value = None
            client.post.return_value = mock_resp
    else:
        # Default: Algolia fails → triggers fallback
        client.post.side_effect = httpx.HTTPError("Algolia unavailable")

    # Mock get() for legacy fallback
    if get_side_effect:
        client.get.side_effect = get_side_effect
    elif get_response is not None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = get_response
        mock_resp.raise_for_status.return_value = None
        client.get.return_value = mock_resp

    return client


# --- _is_latam_location tests ---


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

    def test_south_america_region(self):
        assert _is_latam_location(region="South America") is True

    def test_latam_region_keyword(self):
        assert _is_latam_location(region="LATAM region") is True

    @pytest.mark.parametrize("country", [
        "Argentina", "Chile", "Colombia", "Peru", "Uruguay",
        "Ecuador", "Bolivia", "Paraguay", "Venezuela",
    ])
    def test_all_latam_countries(self, country):
        assert _is_latam_location(country=country) is True


# --- _parse_location tests ---


class TestParseLocation:
    def test_extracts_city_and_country(self):
        hit = {
            "all_locations": "Bogotá, Bogota, Colombia",
            "regions": ["Colombia", "Latin America"],
        }
        city, country = _parse_location(hit)
        assert city == "Bogotá"
        assert country == "Colombia"

    def test_city_only(self):
        hit = {"all_locations": "São Paulo", "regions": []}
        city, country = _parse_location(hit)
        assert city == "São Paulo"
        assert country == ""

    def test_empty_hit(self):
        city, country = _parse_location({})
        assert city == ""
        assert country == ""

    def test_regions_without_latam_country(self):
        hit = {"all_locations": "San Francisco", "regions": ["United States"]}
        city, country = _parse_location(hit)
        assert city == "San Francisco"
        assert country == ""

    def test_brazil_in_regions(self):
        hit = {
            "all_locations": "São Paulo, SP, Brazil",
            "regions": ["Brazil", "Latin America"],
        }
        city, country = _parse_location(hit)
        assert city == "São Paulo"
        assert country == "Brazil"


# --- _hit_to_company tests ---


class TestHitToCompany:
    def test_basic_conversion(self):
        hit = {
            "name": "Neon",
            "slug": "neon",
            "batch": "W19",
            "industry": "Fintech",
            "website": "https://neon.com.br",
            "one_liner": "Digital bank for Brazilians",
            "status": "Active",
            "team_size": 2000,
            "regions": ["Brazil", "Latin America"],
            "all_locations": "São Paulo, SP, Brazil",
        }
        company = _hit_to_company(hit)
        assert company.name == "Neon"
        assert company.slug == "neon"
        assert company.batch == "W19"
        assert company.vertical == "Fintech"
        assert company.website == "https://neon.com.br"
        assert company.description == "Digital bank for Brazilians"
        assert company.team_size == 2000
        assert company.city == "São Paulo"
        assert company.country == "Brazil"
        assert company.region == "Brazil, Latin America"
        assert company.source_url == "https://www.ycombinator.com/companies/neon"

    def test_missing_fields_use_defaults(self):
        hit = {"name": "  MinimalCo  ", "slug": "minimalco"}
        company = _hit_to_company(hit)
        assert company.name == "MinimalCo"
        assert company.batch == ""
        assert company.website == ""
        assert company.team_size is None

    def test_falls_back_to_long_description(self):
        hit = {"name": "X", "slug": "x", "long_description": "Longer desc"}
        company = _hit_to_company(hit)
        assert company.description == "Longer desc"

    def test_industry_fallback_to_vertical(self):
        hit = {"name": "X", "slug": "x", "vertical": "Healthcare"}
        company = _hit_to_company(hit)
        assert company.vertical == "Healthcare"

    def test_generates_slug_from_name(self):
        hit = {"name": "My Startup"}
        company = _hit_to_company(hit)
        assert company.slug == "my-startup"


# --- fetch_yc_companies (Algolia path) tests ---


class TestFetchYcCompaniesAlgolia:
    def test_parses_algolia_response(self):
        hits = [
            _algolia_hit("Neon", "neon", batch="W19", industry="Fintech",
                         regions=["Brazil"], all_locations="São Paulo"),
            _algolia_hit("Rappi", "rappi", batch="S16", industry="Delivery",
                         regions=["Colombia"], all_locations="Bogotá"),
        ]
        client = _mock_client_algolia(
            post_responses=_algolia_response(hits),
        )
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 2
        assert result[0].name == "Neon"
        assert result[0].batch == "W19"
        assert result[1].name == "Rappi"

    def test_skips_entries_without_name(self):
        hits = [
            _algolia_hit("", "no-name"),
            _algolia_hit("Valid", "valid"),
        ]
        client = _mock_client_algolia(
            post_responses=_algolia_response(hits),
        )
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1
        assert result[0].name == "Valid"

    def test_generates_source_url(self):
        hits = [_algolia_hit("Neon", "neon")]
        client = _mock_client_algolia(
            post_responses=_algolia_response(hits),
        )
        result = fetch_yc_companies(_source(), client)
        assert result[0].source_url == "https://www.ycombinator.com/companies/neon"

    def test_paginates_multiple_pages(self):
        page1 = _algolia_response([_algolia_hit("A", "a")], nb_pages=2, page=0)
        page2 = _algolia_response([_algolia_hit("B", "b")], nb_pages=2, page=1)
        client = _mock_client_algolia(post_responses=[page1, page2])

        result = fetch_yc_companies(_source(), client)
        assert len(result) == 2
        assert result[0].name == "A"
        assert result[1].name == "B"
        assert client.post.call_count == 2

    def test_stops_on_empty_hits(self):
        page1 = _algolia_response([_algolia_hit("A", "a")], nb_pages=3)
        page2 = _algolia_response([], nb_pages=3)
        client = _mock_client_algolia(post_responses=[page1, page2])

        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1
        assert client.post.call_count == 2

    def test_handles_algolia_timeout(self):
        client = _mock_client_algolia(
            post_side_effect=httpx.TimeoutException("timeout"),
            get_side_effect=httpx.TimeoutException("timeout"),
        )
        result = fetch_yc_companies(_source(), client)
        assert result == []

    def test_handles_algolia_http_error(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403", request=MagicMock(), response=mock_resp
        )
        client = MagicMock(spec=httpx.Client)
        client.post.return_value = mock_resp
        # Legacy also fails
        client.get.side_effect = httpx.HTTPError("legacy also down")

        result = fetch_yc_companies(_source(), client)
        assert result == []


# --- fetch_yc_companies (legacy fallback) tests ---


class TestFetchYcCompaniesLegacy:
    """Tests that legacy endpoint works when Algolia fails."""

    def test_falls_back_to_legacy(self):
        legacy_data = {
            "companies": [
                {"name": "Neon", "slug": "neon", "batch": "W19", "country": "Brazil"},
                {"name": "Rappi", "slug": "rappi", "batch": "S16", "country": "Colombia"},
            ]
        }
        client = _mock_client_algolia(
            post_side_effect=httpx.HTTPError("Algolia down"),
            get_response=legacy_data,
        )
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 2
        assert result[0].name == "Neon"

    def test_legacy_handles_list_response(self):
        legacy_data = [{"name": "ListCo", "slug": "listco"}]
        client = _mock_client_algolia(
            post_side_effect=httpx.HTTPError("Algolia down"),
            get_response=legacy_data,
        )
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1
        assert result[0].name == "ListCo"

    def test_legacy_skips_empty_names(self):
        legacy_data = {"companies": [{"slug": "no-name"}, {"name": "Valid", "slug": "valid"}]}
        client = _mock_client_algolia(
            post_side_effect=httpx.HTTPError("Algolia down"),
            get_response=legacy_data,
        )
        result = fetch_yc_companies(_source(), client)
        assert len(result) == 1

    def test_both_fail_returns_empty(self):
        client = _mock_client_algolia(
            post_side_effect=httpx.HTTPError("Algolia down"),
            get_side_effect=httpx.TimeoutException("legacy timeout"),
        )
        result = fetch_yc_companies(_source(), client)
        assert result == []

    def test_legacy_handles_http_error(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_resp
        )
        client = MagicMock(spec=httpx.Client)
        client.post.side_effect = httpx.HTTPError("Algolia down")
        client.get.return_value = mock_resp

        result = fetch_yc_companies(_source(), client)
        assert result == []


# --- filter_latam tests ---


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

    def test_region_based_detection(self):
        companies = [
            YCCompany(name="LatamCo", slug="latamco", region="Latin America"),
        ]
        result = filter_latam(companies)
        assert len(result) == 1


# --- Data integrity tests ---


class TestDataIntegrity:
    def test_latam_countries_not_empty(self):
        assert len(LATAM_COUNTRIES) >= 15

    def test_latam_cities_not_empty(self):
        assert len(LATAM_CITIES) >= 10

    def test_brazil_in_countries(self):
        assert "Brazil" in LATAM_COUNTRIES
        assert "Brasil" in LATAM_COUNTRIES

    def test_major_cities_present(self):
        assert "São Paulo" in LATAM_CITIES
        assert "Buenos Aires" in LATAM_CITIES
        assert "Mexico City" in LATAM_CITIES
