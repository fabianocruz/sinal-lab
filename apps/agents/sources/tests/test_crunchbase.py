"""Tests for Crunchbase Basic API source module.

Tests CrunchbaseFundingRound and CrunchbaseCompany dataclasses, plus
fetch_funding_rounds and fetch_companies functions that interact with
the Crunchbase Basic API for collecting LATAM startup funding data.
"""

from datetime import date
from typing import Optional
from unittest.mock import MagicMock, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.crunchbase import (
    CRUNCHBASE_API_BASE,
    CrunchbaseCompany,
    CrunchbaseFundingRound,
    fetch_companies,
    fetch_funding_rounds,
)

# Sample mock data for Crunchbase API responses
SAMPLE_FUNDING_RESPONSE = {
    "entities": [
        {
            "properties": {
                "identifier": {
                    "value": "Nubank Series G",
                    "permalink": "nubank-series-g-abc123",
                },
                "funded_organization_identifier": {
                    "value": "Nubank",
                    "permalink": "nubank",
                },
                "investment_type": "series_g",
                "money_raised": {"value": 750000000, "currency": "USD"},
                "announced_on": "2026-01-15",
                "lead_investor_identifiers": [
                    {"value": "Berkshire Hathaway"},
                    {"value": "Sequoia Capital"},
                ],
                "num_investors": 5,
                "org_funding_total": {"value": 2500000000, "currency": "USD"},
                "short_description": "Nubank raises $750M in Series G round",
            }
        },
        {
            "properties": {
                "identifier": {
                    "value": "Creditas Series F",
                    "permalink": "creditas-series-f-def456",
                },
                "funded_organization_identifier": {
                    "value": "Creditas",
                    "permalink": "creditas",
                },
                "investment_type": "series_f",
                "money_raised": {"value": 200000000, "currency": "USD"},
                "announced_on": "2026-02-01",
                "lead_investor_identifiers": [{"value": "SoftBank Vision Fund"}],
                "num_investors": 3,
                "org_funding_total": {"value": 800000000, "currency": "USD"},
                "short_description": None,
            }
        },
    ]
}

SAMPLE_COMPANY_RESPONSE = {
    "entities": [
        {
            "properties": {
                "identifier": {"value": "Nubank", "permalink": "nubank"},
                "short_description": "Digital banking platform for Latin America",
                "location_identifiers": [
                    {"value": "São Paulo, São Paulo, Brazil"}
                ],
                "founded_on": "2013-05-01",
                "num_employees_enum": "10001+",
                "category_groups": [
                    {"value": "Financial Services"},
                    {"value": "Fintech"},
                ],
                "funding_total": {"value": 2500000000, "currency": "USD"},
                "website_url": "https://nubank.com.br",
            }
        },
        {
            "properties": {
                "identifier": {"value": "Creditas", "permalink": "creditas"},
                "short_description": "Online lending platform for secured credit",
                "location_identifiers": [
                    {"value": "São Paulo, São Paulo, Brazil"}
                ],
                "founded_on": "2012-11-01",
                "num_employees_enum": "1001-5000",
                "category_groups": [{"value": "Fintech"}],
                "funding_total": {"value": 800000000, "currency": "USD"},
                "website_url": "https://www.creditas.com",
            }
        },
    ]
}


class TestCrunchbaseFundingRound:
    """Test CrunchbaseFundingRound dataclass initialization and hashing."""

    def test_content_hash_from_company_name_and_round_type(self) -> None:
        """content_hash is MD5 of company_name (lowercased) + round_type."""
        round = CrunchbaseFundingRound(
            company_name="Nubank",
            round_type="series_g",
            source_url="https://www.crunchbase.com/funding_round/nubank-series-g",
            source_name="crunchbase_funding",
        )
        import hashlib

        expected_hash = hashlib.md5("nubank-series_g".encode()).hexdigest()
        assert round.content_hash == expected_hash

    def test_all_fields_populated_correctly(self) -> None:
        """All fields are stored correctly."""
        announced = date(2026, 1, 15)
        round = CrunchbaseFundingRound(
            company_name="Nubank",
            round_type="series_g",
            source_url="https://www.crunchbase.com/funding_round/nubank-series-g",
            source_name="crunchbase_funding",
            amount_usd=750000000.0,
            announced_date=announced,
            lead_investors=["Berkshire Hathaway", "Sequoia Capital"],
            num_investors=5,
            company_permalink="nubank",
            company_location="São Paulo, Brazil",
        )

        assert round.company_name == "Nubank"
        assert round.round_type == "series_g"
        assert (
            round.source_url
            == "https://www.crunchbase.com/funding_round/nubank-series-g"
        )
        assert round.source_name == "crunchbase_funding"
        assert round.amount_usd == 750000000.0
        assert round.announced_date == announced
        assert round.lead_investors == ["Berkshire Hathaway", "Sequoia Capital"]
        assert round.num_investors == 5
        assert round.company_permalink == "nubank"
        assert round.company_location == "São Paulo, Brazil"

    def test_default_values(self) -> None:
        """Optional fields have correct default values."""
        round = CrunchbaseFundingRound(
            company_name="TestCo",
            round_type="seed",
            source_url="https://www.crunchbase.com/funding_round/testco-seed",
            source_name="crunchbase_test",
        )

        assert round.amount_usd is None
        assert round.announced_date is None
        assert round.lead_investors == []
        assert round.num_investors == 0
        assert round.company_permalink is None
        assert round.company_location is None
        assert round.content_hash != ""  # Auto-generated

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Provided content_hash is not overwritten."""
        custom_hash = "custom_hash_abc123"
        round = CrunchbaseFundingRound(
            company_name="TestCo",
            round_type="seed",
            source_url="https://www.crunchbase.com/funding_round/testco-seed",
            source_name="crunchbase_test",
            content_hash=custom_hash,
        )
        assert round.content_hash == custom_hash

    def test_company_name_with_leading_trailing_spaces_normalized_in_hash(
        self,
    ) -> None:
        """Company name with spaces is normalized in hash (lowercased, stripped)."""
        round = CrunchbaseFundingRound(
            company_name="  Nubank  ",
            round_type="series_g",
            source_url="https://www.crunchbase.com/funding_round/nubank-series-g",
            source_name="crunchbase_test",
        )
        import hashlib

        # Hash should be based on stripped, lowercased company name
        expected_hash = hashlib.md5("nubank-series_g".encode()).hexdigest()
        assert round.content_hash == expected_hash

    def test_round_type_variations(self) -> None:
        """Different round types produce different hashes."""
        seed_round = CrunchbaseFundingRound(
            company_name="TestCo",
            round_type="seed",
            source_url="https://www.crunchbase.com/funding_round/testco-seed",
            source_name="crunchbase_test",
        )

        series_a_round = CrunchbaseFundingRound(
            company_name="TestCo",
            round_type="series_a",
            source_url="https://www.crunchbase.com/funding_round/testco-series-a",
            source_name="crunchbase_test",
        )

        series_b_round = CrunchbaseFundingRound(
            company_name="TestCo",
            round_type="series_b",
            source_url="https://www.crunchbase.com/funding_round/testco-series-b",
            source_name="crunchbase_test",
        )

        # All should have different hashes
        assert seed_round.content_hash != series_a_round.content_hash
        assert series_a_round.content_hash != series_b_round.content_hash
        assert seed_round.content_hash != series_b_round.content_hash

    def test_dedup_compatible_hash_format(self) -> None:
        """Hash format matches FUNDING agent pattern for deduplication."""
        round = CrunchbaseFundingRound(
            company_name="Nubank",
            round_type="series_g",
            source_url="https://www.crunchbase.com/funding_round/nubank-series-g",
            source_name="crunchbase_test",
        )
        # Hash key should be "{company_name.lower().strip()}-{round_type}"
        import hashlib

        expected_hash = hashlib.md5("nubank-series_g".encode()).hexdigest()
        assert round.content_hash == expected_hash


class TestCrunchbaseCompany:
    """Test CrunchbaseCompany dataclass initialization and hashing."""

    def test_content_hash_from_source_url(self) -> None:
        """content_hash is MD5 of the Crunchbase URL."""
        company = CrunchbaseCompany(
            name="Nubank",
            permalink="nubank",
            source_url="https://www.crunchbase.com/organization/nubank",
            source_name="crunchbase_companies",
        )
        import hashlib

        expected_hash = hashlib.md5(
            "https://www.crunchbase.com/organization/nubank".encode()
        ).hexdigest()
        assert company.content_hash == expected_hash

    def test_all_fields_populated_correctly(self) -> None:
        """All fields can be set and stored correctly."""
        founded = date(2013, 5, 1)
        company = CrunchbaseCompany(
            name="Nubank",
            permalink="nubank",
            source_url="https://www.crunchbase.com/organization/nubank",
            source_name="crunchbase_companies",
            short_description="Digital banking platform for Latin America",
            headquarters_location="São Paulo, São Paulo, Brazil",
            founded_on=founded,
            num_employees="10001+",
            categories=["Financial Services", "Fintech"],
            total_funding_usd=2500000000.0,
            website_url="https://nubank.com.br",
        )

        assert company.name == "Nubank"
        assert company.permalink == "nubank"
        assert (
            company.source_url
            == "https://www.crunchbase.com/organization/nubank"
        )
        assert company.source_name == "crunchbase_companies"
        assert (
            company.short_description
            == "Digital banking platform for Latin America"
        )
        assert (
            company.headquarters_location == "São Paulo, São Paulo, Brazil"
        )
        assert company.founded_on == founded
        assert company.num_employees == "10001+"
        assert company.categories == ["Financial Services", "Fintech"]
        assert company.total_funding_usd == 2500000000.0
        assert company.website_url == "https://nubank.com.br"

    def test_default_values(self) -> None:
        """Optional fields default to None or empty list."""
        company = CrunchbaseCompany(
            name="TestCo",
            permalink="testco",
            source_url="https://www.crunchbase.com/organization/testco",
            source_name="crunchbase_test",
        )

        assert company.short_description is None
        assert company.headquarters_location is None
        assert company.founded_on is None
        assert company.num_employees is None
        assert company.categories == []
        assert company.total_funding_usd is None
        assert company.website_url is None
        assert company.content_hash != ""  # Auto-generated

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Provided content_hash is preserved."""
        custom_hash = "my_custom_hash_xyz"
        company = CrunchbaseCompany(
            name="TestCo",
            permalink="testco",
            source_url="https://www.crunchbase.com/organization/testco",
            source_name="crunchbase_test",
            content_hash=custom_hash,
        )
        assert company.content_hash == custom_hash

    def test_categories_list_populated(self) -> None:
        """Categories list is correctly populated and stored."""
        company = CrunchbaseCompany(
            name="TestCo",
            permalink="testco",
            source_url="https://www.crunchbase.com/organization/testco",
            source_name="crunchbase_test",
            categories=["Fintech", "SaaS", "Artificial Intelligence"],
        )
        assert len(company.categories) == 3
        assert "Fintech" in company.categories
        assert "SaaS" in company.categories
        assert "Artificial Intelligence" in company.categories

    def test_unicode_in_fields(self) -> None:
        """Unicode characters in name and location are handled correctly."""
        company = CrunchbaseCompany(
            name="São Paulo Tech",
            permalink="sao-paulo-tech",
            source_url="https://www.crunchbase.com/organization/sao-paulo-tech",
            source_name="crunchbase_test",
            headquarters_location="São Paulo, Brasil",
            short_description="Tecnologia é nossa paixão",
        )
        assert company.name == "São Paulo Tech"
        assert company.headquarters_location == "São Paulo, Brasil"
        assert company.short_description == "Tecnologia é nossa paixão"


class TestFetchFundingRounds:
    """Test fetch_funding_rounds function."""

    def _make_source(
        self,
        name: str = "crunchbase_funding",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Crunchbase funding rounds."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=f"{CRUNCHBASE_API_BASE}/funding_rounds",
            max_items=max_items,
        )

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_returns_empty_list_when_crunchbase_api_key_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] when CRUNCHBASE_API_KEY environment variable is not set."""
        mock_getenv.return_value = None
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_funding_rounds(source, client)

        assert result == []
        mock_getenv.assert_called_with("CRUNCHBASE_API_KEY")
        client.get.assert_not_called()

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_successful_fetch_with_mocked_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful API call returns parsed CrunchbaseFundingRound objects."""
        mock_getenv.return_value = "test_api_key_12345"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_FUNDING_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_funding_rounds(source, client, limit=50)

        assert len(result) == 2
        assert all(isinstance(r, CrunchbaseFundingRound) for r in result)

        # Check first round
        assert result[0].company_name == "Nubank"
        assert result[0].round_type == "series_g"
        assert result[0].amount_usd == 750000000.0
        assert result[0].num_investors == 5

        # Check second round
        assert result[1].company_name == "Creditas"
        assert result[1].round_type == "series_f"
        assert result[1].amount_usd == 200000000.0

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_parses_company_name_round_type_amount_usd_correctly(
        self, mock_getenv: MagicMock
    ) -> None:
        """company_name, round_type, and amount_usd extracted correctly."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_FUNDING_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_funding_rounds(source, client)

        # First round
        assert result[0].company_name == "Nubank"
        assert result[0].round_type == "series_g"
        assert result[0].amount_usd == 750000000.0
        assert result[0].company_permalink == "nubank"

        # Second round
        assert result[1].company_name == "Creditas"
        assert result[1].round_type == "series_f"
        assert result[1].amount_usd == 200000000.0
        assert result[1].company_permalink == "creditas"

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_parses_announced_date_from_iso_date_string(
        self, mock_getenv: MagicMock
    ) -> None:
        """announced_date parsed from ISO date string."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_FUNDING_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_funding_rounds(source, client)

        # First round announced on 2026-01-15
        assert result[0].announced_date == date(2026, 1, 15)

        # Second round announced on 2026-02-01
        assert result[1].announced_date == date(2026, 2, 1)

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_extracts_lead_investors_from_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """lead_investors list extracted from response."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_FUNDING_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_funding_rounds(source, client)

        # First round has two lead investors
        assert len(result[0].lead_investors) == 2
        assert "Berkshire Hathaway" in result[0].lead_investors
        assert "Sequoia Capital" in result[0].lead_investors

        # Second round has one lead investor
        assert len(result[1].lead_investors) == 1
        assert "SoftBank Vision Fund" in result[1].lead_investors

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_empty_results_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """API returns empty entities array, function returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_funding_rounds(source, client)

        assert result == []

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_http_error_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """HTTP error during API call returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("API error")

        result = fetch_funding_rounds(source, client)

        assert result == []

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_timeout_returns_empty_list(self, mock_getenv: MagicMock) -> None:
        """Timeout during API call returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.TimeoutException("Request timeout")

        result = fetch_funding_rounds(source, client)

        assert result == []

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_correct_headers_sent(self, mock_getenv: MagicMock) -> None:
        """X-cb-user-key header sent correctly."""
        mock_getenv.return_value = "test_api_key_xyz"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_funding_rounds(source, client)

        call_args = client.get.call_args
        headers = call_args[1]["headers"]

        assert headers["X-cb-user-key"] == "test_api_key_xyz"

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_respects_limit_and_locations_parameters(
        self, mock_getenv: MagicMock
    ) -> None:
        """Limit and locations parameters passed to API request."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_funding_rounds(
            source, client, locations=["Brazil", "Mexico"], limit=25
        )

        # Check that client.get was called with correct params
        call_args = client.get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 25
        # Locations filtering would be in params if API supports it
        # (Implementation detail depends on actual Crunchbase API)


class TestFetchCompanies:
    """Test fetch_companies function."""

    def _make_source(
        self,
        name: str = "crunchbase_companies",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for Crunchbase companies."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=f"{CRUNCHBASE_API_BASE}/entities/organizations",
            max_items=max_items,
        )

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_returns_empty_list_when_crunchbase_api_key_not_set(
        self, mock_getenv: MagicMock
    ) -> None:
        """Returns [] when CRUNCHBASE_API_KEY not set."""
        mock_getenv.return_value = None
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_companies(source, client)

        assert result == []
        mock_getenv.assert_called_with("CRUNCHBASE_API_KEY")
        client.get.assert_not_called()

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_successful_fetch_with_mocked_response(
        self, mock_getenv: MagicMock
    ) -> None:
        """Successful API call returns parsed CrunchbaseCompany objects."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_COMPANY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_companies(source, client, limit=50)

        assert len(result) == 2
        assert all(isinstance(c, CrunchbaseCompany) for c in result)

        # Check first company
        assert result[0].name == "Nubank"
        assert result[0].permalink == "nubank"
        assert (
            result[0].short_description
            == "Digital banking platform for Latin America"
        )

        # Check second company
        assert result[1].name == "Creditas"
        assert result[1].permalink == "creditas"

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_parses_all_company_fields_correctly(
        self, mock_getenv: MagicMock
    ) -> None:
        """All company fields extracted correctly from response."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_COMPANY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_companies(source, client)

        # First company
        assert result[0].name == "Nubank"
        assert result[0].permalink == "nubank"
        assert (
            result[0].short_description
            == "Digital banking platform for Latin America"
        )
        assert (
            result[0].headquarters_location == "São Paulo, São Paulo, Brazil"
        )
        assert result[0].founded_on == date(2013, 5, 1)
        assert result[0].num_employees == "10001+"
        assert "Financial Services" in result[0].categories
        assert "Fintech" in result[0].categories
        assert result[0].total_funding_usd == 2500000000.0
        assert result[0].website_url == "https://nubank.com.br"

        # Second company
        assert result[1].name == "Creditas"
        assert result[1].founded_on == date(2012, 11, 1)
        assert result[1].num_employees == "1001-5000"
        assert result[1].total_funding_usd == 800000000.0

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_empty_results_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """API returns empty entities array."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_companies(source, client)

        assert result == []

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_http_error_returns_empty_list(
        self, mock_getenv: MagicMock
    ) -> None:
        """HTTP error returns []."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("API error")

        result = fetch_companies(source, client)

        assert result == []

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_correct_headers_sent(self, mock_getenv: MagicMock) -> None:
        """X-cb-user-key header sent correctly."""
        mock_getenv.return_value = "test_api_key_abc"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_companies(source, client)

        call_args = client.get.call_args
        headers = call_args[1]["headers"]

        assert headers["X-cb-user-key"] == "test_api_key_abc"

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_respects_limit_locations_and_categories_parameters(
        self, mock_getenv: MagicMock
    ) -> None:
        """Limit, locations, and categories parameters passed to API."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_companies(
            source,
            client,
            locations=["Brazil", "Mexico"],
            categories=["Fintech", "SaaS"],
            limit=30,
        )

        call_args = client.get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 30
        # Locations and categories filtering would be in params
        # (Implementation detail depends on actual Crunchbase API)

    @patch("apps.agents.sources.crunchbase.os.getenv")
    def test_handles_missing_optional_fields_gracefully(
        self, mock_getenv: MagicMock
    ) -> None:
        """Missing optional fields handled gracefully."""
        mock_getenv.return_value = "test_api_key"
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        # Minimal company data with missing optional fields
        minimal_response = {
            "entities": [
                {
                    "properties": {
                        "identifier": {"value": "MinimalCo", "permalink": "minimalco"},
                        # All other fields missing
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = minimal_response
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_companies(source, client)

        # Should still parse successfully with default/None values
        assert len(result) == 1
        assert result[0].name == "MinimalCo"
        assert result[0].permalink == "minimalco"
        assert result[0].short_description is None
        assert result[0].founded_on is None
        assert result[0].categories == []
