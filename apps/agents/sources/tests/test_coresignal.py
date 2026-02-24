"""Tests for CoreSignal API source module.

Tests CoreSignalCompany dataclass, search_companies, collect_company, and
fetch_coresignal_companies functions that interact with the CoreSignal API
for collecting LATAM startup data.

API flow:
  Search: POST .../company_base/search/filter -> [id1, id2, ...]
  Collect: GET .../company_base/collect/{id}  -> company JSON

Key implementation details (from coresignal.py):
  - String fields default to "" (not None); numeric optionals default to None.
  - search_companies posts to CORESIGNAL_SEARCH_URL with {"apikey": key} headers.
  - collect_company GETs CORESIGNAL_COLLECT_URL/{id} with {"apikey": key} headers.
  - source_url and linkedin_url both come from the "url" field in the API response.
  - country comes from "headquarters_country_parsed"; city from "headquarters_new_address".
  - deleted flag is NOT in coresignal.py — collect_company does NOT skip deleted=1
    (deletion filtering is left to the caller / pipeline layer).
  - fetch_coresignal_companies reads CORESIGNAL_API_KEY from os.getenv.
"""

from typing import List, Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.coresignal import (
    CORESIGNAL_COLLECT_URL,
    CORESIGNAL_SEARCH_URL,
    CoreSignalCompany,
    collect_company,
    fetch_coresignal_companies,
    search_companies,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _source() -> DataSourceConfig:
    """Minimal DataSourceConfig for CoreSignal."""
    return DataSourceConfig(
        name="coresignal_latam",
        source_type="api",
        url="https://api.coresignal.com/cdapi/v2/company_base",
    )


def _full_company_json(*, company_id: int = 42) -> dict:
    """Return a representative CoreSignal company_base/collect JSON payload.

    Note: 'url' is the LinkedIn URL — it is mapped to both linkedin_url and
    source_url in _parse_company.
    """
    return {
        "id": company_id,
        "name": "Nubank",
        "website": "https://nubank.com.br",
        "description": "Digital banking platform for Latin America.",
        "industry": "Financial Services",
        "headquarters_country_parsed": "Brazil",
        "headquarters_new_address": "Sao Paulo, SP, Brazil",
        "employees_count": 8000,
        "founded": 2013,
        "url": "https://www.linkedin.com/company/nubank",
        "logo_url": "https://cdn.coresignal.com/logos/nubank.png",
        "type": "Private",
    }


def _make_search_client(
    ids: List[int],
    status_code: int = 200,
    side_effect: Optional[Exception] = None,
) -> MagicMock:
    """Return a mock httpx.Client whose POST returns the given ID list."""
    client = MagicMock(spec=httpx.Client)
    if side_effect is not None:
        client.post.side_effect = side_effect
        return client
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = ids
    mock_resp.raise_for_status.return_value = None
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    client.post.return_value = mock_resp
    return client


def _make_collect_client(
    company_json: dict,
    status_code: int = 200,
    side_effect: Optional[Exception] = None,
) -> MagicMock:
    """Return a mock httpx.Client whose GET returns the given company JSON."""
    client = MagicMock(spec=httpx.Client)
    if side_effect is not None:
        client.get.side_effect = side_effect
        return client
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = company_json
    mock_resp.raise_for_status.return_value = None
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    client.get.return_value = mock_resp
    return client


# ---------------------------------------------------------------------------
# TestCoreSignalCompany
# ---------------------------------------------------------------------------


class TestCoreSignalCompany:
    """Test CoreSignalCompany dataclass fields and defaults."""

    def test_required_fields_stored_correctly(self) -> None:
        """name, slug, source_url, and coresignal_id are stored as provided."""
        company = CoreSignalCompany(
            name="Nubank",
            slug="nubank",
            source_url=f"{CORESIGNAL_COLLECT_URL}/42",
            coresignal_id=42,
        )

        assert company.name == "Nubank"
        assert company.slug == "nubank"
        assert company.source_url == f"{CORESIGNAL_COLLECT_URL}/42"
        assert company.coresignal_id == 42

    def test_string_optional_fields_default_to_none(self) -> None:
        """String optional fields (website, description, etc.) default to None."""
        company = CoreSignalCompany(
            name="TestCo",
            slug="testco",
        )

        assert company.website is None
        assert company.description is None
        assert company.industry is None
        assert company.country is None
        assert company.city is None
        assert company.linkedin_url is None
        assert company.logo_url is None
        assert company.company_type is None

    def test_numeric_optional_fields_default_to_none(self) -> None:
        """employees_count and founded_year default to None."""
        company = CoreSignalCompany(
            name="TestCo",
            slug="testco",
        )

        assert company.employees_count is None
        assert company.founded_year is None

    def test_coresignal_id_defaults_to_zero(self) -> None:
        """coresignal_id defaults to 0 when not provided."""
        company = CoreSignalCompany(
            name="TestCo",
            slug="testco",
        )

        assert company.coresignal_id == 0

    def test_all_optional_fields_stored_correctly(self) -> None:
        """All optional fields are stored as provided when given."""
        company = CoreSignalCompany(
            name="Nubank",
            slug="nubank",
            website="https://nubank.com.br",
            description="Digital banking platform for Latin America.",
            industry="Financial Services",
            country="Brazil",
            city="Sao Paulo",
            employees_count=8000,
            founded_year=2013,
            linkedin_url="https://www.linkedin.com/company/nubank",
            logo_url="https://cdn.coresignal.com/logos/nubank.png",
            company_type="Private",
            source_url=f"{CORESIGNAL_COLLECT_URL}/42",
            coresignal_id=42,
        )

        assert company.website == "https://nubank.com.br"
        assert company.description == "Digital banking platform for Latin America."
        assert company.industry == "Financial Services"
        assert company.country == "Brazil"
        assert company.city == "Sao Paulo"
        assert company.employees_count == 8000
        assert company.founded_year == 2013
        assert company.linkedin_url == "https://www.linkedin.com/company/nubank"
        assert company.logo_url == "https://cdn.coresignal.com/logos/nubank.png"
        assert company.company_type == "Private"

    def test_unicode_in_name_and_city(self) -> None:
        """Unicode characters in name and city are preserved correctly."""
        company = CoreSignalCompany(
            name="Tecnologia Brasileira",
            slug="tecnologia-brasileira",
            city="Sao Paulo",
            country="Brasil",
        )

        assert company.name == "Tecnologia Brasileira"
        assert company.city == "Sao Paulo"
        assert company.country == "Brasil"


# ---------------------------------------------------------------------------
# TestSearchCompanies
# ---------------------------------------------------------------------------


class TestSearchCompanies:
    """Test search_companies — POST to CoreSignal search filter endpoint."""

    def test_returns_list_of_ids(self) -> None:
        """Successful search returns the list of integer IDs from the API."""
        client = _make_search_client([1, 2, 3])

        result = search_companies(client, "test_key", country="Brazil")

        assert result == [1, 2, 3]
        client.post.assert_called_once()

    def test_posts_to_correct_search_endpoint(self) -> None:
        """POST is made to the CORESIGNAL_SEARCH_URL constant."""
        client = _make_search_client([10])

        search_companies(client, "test_key", country="Mexico")

        call_args = client.post.call_args
        posted_url = call_args[0][0]
        assert posted_url == CORESIGNAL_SEARCH_URL

    def test_includes_country_in_request_body(self) -> None:
        """Country filter is sent in the POST JSON body."""
        client = _make_search_client([5, 6])

        search_companies(client, "test_key", country="Colombia")

        call_args = client.post.call_args
        body = call_args[1].get("json", {})
        assert "country" in body
        assert "Colombia" in body["country"]

    def test_includes_apikey_in_headers(self) -> None:
        """'apikey' header sent with the provided API key value."""
        client = _make_search_client([7])

        search_companies(client, "secret_key_xyz", country="Brazil")

        call_args = client.post.call_args
        headers = call_args[1].get("headers", {})
        assert headers.get("apikey") == "secret_key_xyz"

    def test_includes_content_type_in_headers(self) -> None:
        """Content-Type: application/json header is sent."""
        client = _make_search_client([])

        search_companies(client, "test_key", country="Brazil")

        headers = client.post.call_args[1].get("headers", {})
        assert headers.get("Content-Type") == "application/json"

    def test_empty_response_returns_empty_list(self) -> None:
        """API returning [] is handled gracefully — returns empty list."""
        client = _make_search_client([])

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_handles_timeout(self) -> None:
        """Timeout during POST returns empty list without raising."""
        client = _make_search_client(
            [], side_effect=httpx.TimeoutException("timeout")
        )

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_handles_http_error(self) -> None:
        """Generic HTTP error during POST returns empty list without raising."""
        client = _make_search_client(
            [], side_effect=httpx.HTTPError("500 Server Error")
        )

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_handles_http_status_error_from_raise_for_status(self) -> None:
        """HTTPStatusError raised by raise_for_status returns empty list."""
        client = _make_search_client([], status_code=429)

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_optional_industry_filter_included_in_body(self) -> None:
        """industry parameter, when supplied, is included in the POST body."""
        client = _make_search_client([20, 21])

        search_companies(client, "test_key", country="Brazil", industry="Fintech")

        body = client.post.call_args[1].get("json", {})
        assert "industry" in body
        assert "Fintech" in body["industry"]

    def test_industry_omitted_from_body_when_not_provided(self) -> None:
        """industry key is absent from body when not passed."""
        client = _make_search_client([])

        search_companies(client, "test_key", country="Brazil")

        body = client.post.call_args[1].get("json", {})
        assert "industry" not in body

    def test_non_list_response_returns_empty_list(self) -> None:
        """Non-list API response (e.g. dict error body) returns empty list."""
        client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "bad request"}
        mock_resp.raise_for_status.return_value = None
        client.post.return_value = mock_resp

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_filters_out_non_integer_values_from_response(self) -> None:
        """Strings and None items are filtered; ints (including floats? no) kept.

        isinstance(item, int) keeps Python int objects only:
        1 and 2 pass; strings and None fail; 3.5 (float) fails too.
        """
        client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = [1, "not_an_int", None, 2, 3.5]
        mock_resp.raise_for_status.return_value = None
        client.post.return_value = mock_resp

        result = search_companies(client, "test_key", country="Brazil")

        # Only pure Python int values (1, 2) survive; "not_an_int", None, 3.5 do not
        assert result == [1, 2]
        assert "not_an_int" not in result
        assert None not in result
        assert 3.5 not in result

    def test_unexpected_exception_returns_empty_list(self) -> None:
        """Any unexpected exception during POST returns [] without propagating."""
        client = MagicMock(spec=httpx.Client)
        client.post.side_effect = RuntimeError("unexpected internal error")

        result = search_companies(client, "test_key", country="Brazil")

        assert result == []

    def test_employee_count_range_included_in_body(self) -> None:
        """employees_count_gte and employees_count_lte are included in the POST body."""
        client = _make_search_client([])

        search_companies(
            client,
            "test_key",
            country="Brazil",
            employees_count_gte=10,
            employees_count_lte=500,
        )

        body = client.post.call_args[1].get("json", {})
        assert body.get("employees_count_gte") == 10
        assert body.get("employees_count_lte") == 500

    def test_founded_year_range_included_in_body(self) -> None:
        """founded_year_gte and founded_year_lte are included in the POST body."""
        client = _make_search_client([])

        search_companies(
            client,
            "test_key",
            country="Brazil",
            founded_year_gte=2010,
            founded_year_lte=2020,
        )

        body = client.post.call_args[1].get("json", {})
        assert body.get("founded_year_gte") == 2010
        assert body.get("founded_year_lte") == 2020


# ---------------------------------------------------------------------------
# TestCollectCompany
# ---------------------------------------------------------------------------


class TestCollectCompany:
    """Test collect_company — GET from CoreSignal collect/{id} endpoint."""

    def test_parses_company_data_from_full_response(self) -> None:
        """All company fields are parsed correctly from a full API response."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert isinstance(result, CoreSignalCompany)
        assert result.name == "Nubank"
        assert result.website == "https://nubank.com.br"
        assert result.description == "Digital banking platform for Latin America."
        assert result.industry == "Financial Services"
        assert result.coresignal_id == 42

    def test_parses_employees_count_and_founded_year(self) -> None:
        """employees_count and founded_year parsed from numeric API fields."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.employees_count == 8000
        assert result.founded_year == 2013

    def test_parses_linkedin_url_from_url_field(self) -> None:
        """linkedin_url comes from the 'url' field in the API response."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.linkedin_url == "https://www.linkedin.com/company/nubank"

    def test_parses_logo_url(self) -> None:
        """logo_url is extracted from the API response."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.logo_url == "https://cdn.coresignal.com/logos/nubank.png"

    def test_parses_company_type(self) -> None:
        """company_type field (e.g., 'Private') is extracted correctly."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.company_type == "Private"

    def test_parses_headquarters_country_from_headquarters_country_parsed(
        self,
    ) -> None:
        """country is extracted from the 'headquarters_country_parsed' field."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.country == "Brazil"

    def test_parses_city_from_headquarters_new_address(self) -> None:
        """city is the first part (before comma) of headquarters_new_address."""
        client = _make_collect_client(_full_company_json())

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        # "Sao Paulo, SP, Brazil" -> city = "Sao Paulo"
        assert result.city == "Sao Paulo"

    def test_city_is_none_when_address_is_missing(self) -> None:
        """city is None when headquarters_new_address is absent from the payload."""
        data = {**_full_company_json()}
        del data["headquarters_new_address"]
        client = _make_collect_client(data)

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert result.city is None

    def test_get_called_with_correct_collect_url(self) -> None:
        """GET is made to CORESIGNAL_COLLECT_URL/{company_id}."""
        client = _make_collect_client(_full_company_json(company_id=77))

        collect_company(client, "test_key", company_id=77)

        call_args = client.get.call_args
        requested_url = call_args[0][0]
        assert requested_url == f"{CORESIGNAL_COLLECT_URL}/77"

    def test_includes_apikey_in_headers(self) -> None:
        """'apikey' header sent with the provided API key value."""
        client = _make_collect_client(_full_company_json())

        collect_company(client, "secret_collect_key", company_id=42)

        headers = client.get.call_args[1].get("headers", {})
        assert headers.get("apikey") == "secret_collect_key"

    def test_handles_404_returns_none(self) -> None:
        """404 response returns None without raising."""
        client = _make_collect_client({}, status_code=404)

        result = collect_company(client, "test_key", company_id=9999)

        assert result is None

    def test_handles_timeout(self) -> None:
        """Timeout during GET returns None without raising."""
        client = _make_collect_client(
            {}, side_effect=httpx.TimeoutException("timeout")
        )

        result = collect_company(client, "test_key", company_id=1)

        assert result is None

    def test_handles_http_error(self) -> None:
        """Generic HTTP error returns None without raising."""
        client = _make_collect_client(
            {}, side_effect=httpx.HTTPError("connection error")
        )

        result = collect_company(client, "test_key", company_id=1)

        assert result is None

    def test_returns_none_when_name_is_missing(self) -> None:
        """Company with no name field is skipped — returns None."""
        data = {
            "id": 5,
            "website": "https://example.com",
            "deleted": 0,
        }
        client = _make_collect_client(data)

        result = collect_company(client, "test_key", company_id=5)

        assert result is None

    def test_handles_missing_optional_fields_in_response(self) -> None:
        """Response with only minimal fields produces a valid object with None optionals."""
        minimal_json = {
            "id": 7,
            "name": "MinimalCo",
        }
        client = _make_collect_client(minimal_json)

        result = collect_company(client, "test_key", company_id=7)

        assert result is not None
        assert result.name == "MinimalCo"
        assert result.coresignal_id == 7
        assert result.website is None
        assert result.description is None
        assert result.country is None
        assert result.city is None
        assert result.employees_count is None
        assert result.founded_year is None

    def test_description_truncated_at_1000_chars(self) -> None:
        """Descriptions longer than 1000 characters are truncated to 997 + '...'."""
        long_desc = "A" * 1200
        data = {**_full_company_json(), "description": long_desc}
        client = _make_collect_client(data)

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert len(result.description) == 1000
        assert result.description.endswith("...")

    def test_description_not_truncated_at_exactly_1000_chars(self) -> None:
        """Descriptions of exactly 1000 characters are NOT truncated."""
        exact_desc = "B" * 1000
        data = {**_full_company_json(), "description": exact_desc}
        client = _make_collect_client(data)

        result = collect_company(client, "test_key", company_id=42)

        assert result is not None
        assert len(result.description) == 1000
        assert not result.description.endswith("...")

    def test_skips_deleted_company(self) -> None:
        """Companies with deleted=1 in the API payload return None."""
        data = {**_full_company_json(), "deleted": 1}
        client = _make_collect_client(data)

        result = collect_company(client, "test_key", company_id=42)

        assert result is None

    def test_non_404_http_status_error_returns_none(self) -> None:
        """Non-404 HTTPStatusError (e.g. 500) returns None without raising."""
        client = MagicMock(spec=httpx.Client)
        error_resp = MagicMock()
        error_resp.status_code = 500
        client.get.side_effect = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=error_resp
        )

        result = collect_company(client, "test_key", company_id=42)

        assert result is None

    def test_unexpected_exception_returns_none(self) -> None:
        """Unexpected exception during GET returns None without propagating."""
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = RuntimeError("unexpected failure")

        result = collect_company(client, "test_key", company_id=42)

        assert result is None

    def test_non_dict_response_returns_none(self) -> None:
        """When the API returns a non-dict (e.g. a list), collect returns None."""
        client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [1, 2, 3]  # list instead of dict
        client.get.return_value = mock_resp

        result = collect_company(client, "test_key", company_id=42)

        assert result is None


# ---------------------------------------------------------------------------
# TestFetchCoresignalCompanies
# ---------------------------------------------------------------------------


class TestFetchCoresignalCompanies:
    """Test fetch_coresignal_companies — the main orchestrating function."""

    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_no_api_key_returns_empty(self, mock_getenv: MagicMock) -> None:
        """Returns [] immediately when CORESIGNAL_API_KEY is not set."""
        mock_getenv.return_value = None
        source = _source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_coresignal_companies(source, client)

        assert result == []
        mock_getenv.assert_called_with("CORESIGNAL_API_KEY")
        client.post.assert_not_called()
        client.get.assert_not_called()

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_search_and_collect_flow(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """search returns IDs, collect is called for each ID, returns companies."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        # All country searches return the same two IDs (dedup will produce [1, 2])
        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = [1, 2]
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        collect_resp_1 = MagicMock(spec=httpx.Response)
        collect_resp_1.status_code = 200
        collect_resp_1.json.return_value = {
            **_full_company_json(company_id=1),
            "name": "Nubank",
        }
        collect_resp_1.raise_for_status.return_value = None

        collect_resp_2 = MagicMock(spec=httpx.Response)
        collect_resp_2.status_code = 200
        collect_resp_2.json.return_value = {
            **_full_company_json(company_id=2),
            "name": "iFood",
        }
        collect_resp_2.raise_for_status.return_value = None

        client.get.side_effect = [collect_resp_1, collect_resp_2]

        result = fetch_coresignal_companies(source, client, max_collect=200)

        assert len(result) == 2
        assert all(isinstance(c, CoreSignalCompany) for c in result)
        names = {c.name for c in result}
        assert "Nubank" in names
        assert "iFood" in names

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_deduplicates_ids_across_countries(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Same company ID returned by multiple country searches is collected once."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        # Every country search returns IDs [99, 100] — duplicates across all searches
        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = [99, 100]
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        def make_collect(cid: int) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {**_full_company_json(company_id=cid), "name": f"Co{cid}"}
            return resp

        client.get.side_effect = [make_collect(99), make_collect(100)]

        result = fetch_coresignal_companies(source, client, max_collect=200)

        # Only 2 unique IDs regardless of how many country searches ran
        unique_ids = {c.coresignal_id for c in result}
        assert len(unique_ids) == 2
        assert client.get.call_count == 2

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_respects_max_collect_limit(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Collects at most max_collect companies even if more unique IDs are found."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        # Search yields IDs 1-20
        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = list(range(1, 21))
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        def make_collect(cid: int) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {**_full_company_json(company_id=cid), "name": f"Co{cid}"}
            return resp

        client.get.side_effect = [make_collect(i) for i in range(1, 21)]

        result = fetch_coresignal_companies(source, client, max_collect=5)

        assert len(result) <= 5
        assert client.get.call_count <= 5

    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_handles_search_failure_gracefully(
        self, mock_getenv: MagicMock
    ) -> None:
        """If all search POSTs fail, returns [] without raising."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)
        client.post.side_effect = httpx.HTTPError("search endpoint down")

        result = fetch_coresignal_companies(source, client)

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_skips_failed_collect_and_continues(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """If collecting one company fails, the remaining companies are still returned."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = [1, 2]
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        failed_resp = MagicMock(spec=httpx.Response)
        failed_resp.status_code = 404
        failed_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "not found", request=MagicMock(), response=failed_resp
        )

        good_resp = MagicMock(spec=httpx.Response)
        good_resp.status_code = 200
        good_resp.raise_for_status.return_value = None
        good_resp.json.return_value = _full_company_json(company_id=2)

        # IDs are sorted before collecting: [1, 2]; ID 1 fails, ID 2 succeeds
        client.get.side_effect = [failed_resp, good_resp]

        result = fetch_coresignal_companies(source, client, max_collect=200)

        assert len(result) == 1
        assert result[0].coresignal_id == 2

    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_returns_empty_when_all_searches_return_no_ids(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] without calling collect when all searches return empty lists."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = []
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        result = fetch_coresignal_companies(source, client)

        assert result == []
        client.get.assert_not_called()

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_rate_limit_sleep_called_between_collect_calls(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """time.sleep is called between collect requests to respect rate limits."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = [1, 2, 3]
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        def make_collect(cid: int) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {**_full_company_json(company_id=cid), "name": f"Co{cid}"}
            return resp

        client.get.side_effect = [make_collect(i) for i in [1, 2, 3]]

        fetch_coresignal_companies(source, client, max_collect=200)

        # sleep should be called N-1 times for N companies (not after last)
        assert mock_sleep.call_count == 2

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_stops_early_after_consecutive_failures(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Stops collecting after 10 consecutive failures (e.g. 402 credit exhaustion)."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        # Search returns 20 IDs
        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = list(range(1, 21))
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        # All collect calls fail with 402
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.status_code = 402
        fail_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Payment Required", request=MagicMock(), response=fail_resp
        )
        client.get.return_value = fail_resp

        result = fetch_coresignal_companies(source, client, max_collect=20)

        assert result == []
        # Should stop after 10 consecutive failures, not try all 20
        assert client.get.call_count == 10

    @patch("apps.agents.sources.coresignal.time.sleep")
    @patch("apps.agents.sources.coresignal.os.getenv")
    def test_resets_failure_counter_on_success(
        self, mock_getenv: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """A successful collect resets the consecutive failure counter."""
        mock_getenv.return_value = "api_key_abc"
        source = _source()
        client = MagicMock(spec=httpx.Client)

        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = list(range(1, 16))
        search_resp.raise_for_status.return_value = None
        client.post.return_value = search_resp

        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.status_code = 402
        fail_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Payment Required", request=MagicMock(), response=fail_resp
        )

        def make_ok(cid: int) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {**_full_company_json(company_id=cid), "name": f"Co{cid}"}
            return resp

        # 9 failures, then 1 success, then 9 more failures => should NOT early-stop
        # because the success resets the counter
        responses = (
            [fail_resp] * 9 + [make_ok(6)] + [fail_resp] * 5
        )
        client.get.side_effect = responses

        result = fetch_coresignal_companies(source, client, max_collect=15)

        assert len(result) == 1
        assert client.get.call_count == 15
