"""Tests for SEC EDGAR Form D source module.

Tests SECFormDFiling dataclass (auto-hash, authority, defaults) and
fetch_sec_form_d function that queries the SEC EDGAR full-text search
API for Regulation D filings.
"""

from datetime import date
from typing import Optional
from unittest.mock import MagicMock, call, patch

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.dedup import compute_composite_hash
from apps.agents.sources.sec_form_d import (
    SEC_EFTS_BASE,
    SECFormDFiling,
    fetch_sec_form_d,
)
from apps.agents.sources.verification import VerificationLevel

# ---------------------------------------------------------------------------
# Sample mock data
# ---------------------------------------------------------------------------

SAMPLE_SEC_RESPONSE = {
    "hits": {
        "hits": [
            {
                "_source": {
                    "display_names": ["Nu Holdings Ltd"],
                    "file_date": "2026-01-20",
                    "form_type": "D",
                    "entity_id": "0001234567",
                    "file_num": "021-12345",
                    "display_date_filed": "2026-01-20",
                },
                "_id": "0001234567-26-000123",
            }
        ],
        "total": {"value": 1},
    }
}

SAMPLE_SEC_TWO_HITS = {
    "hits": {
        "hits": [
            {
                "_source": {
                    "display_names": ["Nu Holdings Ltd"],
                    "file_date": "2026-01-20",
                    "form_type": "D",
                    "entity_id": "0001234567",
                    "display_date_filed": "2026-01-20",
                    "amount_sold": 500000000,
                },
                "_id": "0001234567-26-000123",
            },
            {
                "_source": {
                    "display_names": ["Nu Holdings Ltd."],
                    "file_date": "2026-01-25",
                    "form_type": "D",
                    "entity_id": "0009876543",
                    "display_date_filed": "2026-01-25",
                    "amount_sold": 0,
                },
                "_id": "0009876543-26-000456",
            },
        ],
        "total": {"value": 2},
    }
}


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestSECFormDFiling:
    """Test SECFormDFiling dataclass initialization and auto-fields."""

    def test_content_hash_auto_computed(self) -> None:
        """content_hash equals compute_composite_hash(cik, str(date_filed))."""
        filing = SECFormDFiling(
            company_name="Nu Holdings Ltd",
            cik="0001234567",
            source_url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001234567&type=D&dateb=&owner=include&count=10",
            date_filed=date(2026, 1, 20),
        )
        expected = compute_composite_hash("0001234567", "2026-01-20")
        assert filing.content_hash == expected

    def test_authority_auto_created(self) -> None:
        """authority is REGULATORY with institution SEC."""
        filing = SECFormDFiling(
            company_name="Nu Holdings Ltd",
            cik="0001234567",
            source_url="https://example.com",
            date_filed=date(2026, 1, 20),
        )
        assert filing.authority.verification_level == VerificationLevel.REGULATORY
        assert filing.authority.institution_name == "SEC"
        assert filing.authority.regulatory_id == "CIK-0001234567"

    def test_all_fields_populated(self) -> None:
        """All fields are stored correctly when explicitly provided."""
        filing = SECFormDFiling(
            company_name="Nu Holdings Ltd",
            cik="0001234567",
            source_url="https://example.com/filing",
            date_filed=date(2026, 1, 20),
            amount_sold=500000000.0,
            related_persons=["David Velez", "Cristina Junqueira"],
        )
        assert filing.company_name == "Nu Holdings Ltd"
        assert filing.cik == "0001234567"
        assert filing.source_url == "https://example.com/filing"
        assert filing.date_filed == date(2026, 1, 20)
        assert filing.amount_sold == 500000000.0
        assert filing.related_persons == ["David Velez", "Cristina Junqueira"]

    def test_default_values(self) -> None:
        """Optional fields have correct defaults."""
        filing = SECFormDFiling(
            company_name="TestCo",
            cik="0000000001",
            source_url="https://example.com",
            date_filed=date(2026, 2, 1),
        )
        assert filing.related_persons == []
        assert filing.amount_sold is None
        assert filing.content_hash != ""  # auto-generated

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Provided content_hash is preserved, not overwritten."""
        custom_hash = "custom_hash_abc123"
        filing = SECFormDFiling(
            company_name="TestCo",
            cik="0000000001",
            source_url="https://example.com",
            date_filed=date(2026, 2, 1),
            content_hash=custom_hash,
        )
        assert filing.content_hash == custom_hash

    def test_amount_sold_none_for_undisclosed(self) -> None:
        """amount_sold=None is valid for undisclosed amounts."""
        filing = SECFormDFiling(
            company_name="TestCo",
            cik="0000000001",
            source_url="https://example.com",
            date_filed=date(2026, 2, 1),
            amount_sold=None,
        )
        assert filing.amount_sold is None


# ---------------------------------------------------------------------------
# fetch_sec_form_d tests
# ---------------------------------------------------------------------------


class TestFetchSecFormD:
    """Test fetch_sec_form_d function."""

    def _make_source(
        self,
        name: str = "sec_form_d",
        max_items: Optional[int] = None,
    ) -> DataSourceConfig:
        """Helper to create a DataSourceConfig for SEC EDGAR."""
        return DataSourceConfig(
            name=name,
            source_type="api",
            url=SEC_EFTS_BASE,
            max_items=max_items,
        )

    def test_successful_fetch(self) -> None:
        """Successful API call returns parsed SECFormDFiling objects."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_SEC_TWO_HITS
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(
            source, client, ["Nu Holdings Ltd"]
        )

        assert len(result) == 2
        assert all(isinstance(f, SECFormDFiling) for f in result)
        assert result[0].company_name == "Nu Holdings Ltd"
        assert result[0].cik == "0001234567"
        assert result[0].date_filed == date(2026, 1, 20)
        assert result[0].amount_sold == 500000000.0

        # Second hit: amount_sold=0 is stored as None (undisclosed)
        assert result[1].company_name == "Nu Holdings Ltd."
        assert result[1].cik == "0009876543"
        assert result[1].date_filed == date(2026, 1, 25)
        assert result[1].amount_sold is None

    def test_returns_empty_list_on_http_error(self) -> None:
        """HTTP error returns [] (graceful degradation)."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = httpx.HTTPError("Server error")

        result = fetch_sec_form_d(source, client, ["Nubank"])

        assert result == []

    def test_returns_empty_list_on_timeout(self) -> None:
        """Timeout returns [] (graceful degradation)."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = httpx.TimeoutException("Request timeout")

        result = fetch_sec_form_d(source, client, ["Nubank"])

        assert result == []

    def test_returns_empty_list_for_empty_company_names(self) -> None:
        """Empty company_names list returns [] immediately."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        result = fetch_sec_form_d(source, client, [])

        assert result == []
        client.get.assert_not_called()

    def test_filters_unrelated_filings_by_fuzzy_match(self) -> None:
        """Filings with unrelated company names are filtered out."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        # Response contains both a matching and a non-matching filing
        mixed_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "display_names": ["Nu Holdings Ltd"],
                            "file_date": "2026-01-20",
                            "entity_id": "0001234567",
                        },
                        "_id": "0001234567-26-000123",
                    },
                    {
                        "_source": {
                            "display_names": ["Apple Inc"],
                            "file_date": "2026-01-22",
                            "entity_id": "0000320193",
                        },
                        "_id": "0000320193-26-000789",
                    },
                ],
                "total": {"value": 2},
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mixed_response
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(
            source, client, ["Nu Holdings Ltd"]
        )

        # Only "Nu Holdings Ltd" should pass the fuzzy match; "Apple Inc" filtered
        assert len(result) == 1
        assert result[0].company_name == "Nu Holdings Ltd"

    def test_amount_zero_stored_as_none(self) -> None:
        """Amount of 0 is treated as undisclosed and stored as None."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        response_with_zero = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "display_names": ["Nu Holdings Ltd"],
                            "file_date": "2026-01-20",
                            "entity_id": "0001234567",
                            "amount_sold": 0,
                        },
                        "_id": "0001234567-26-000123",
                    }
                ],
                "total": {"value": 1},
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_with_zero
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(
            source, client, ["Nu Holdings Ltd"]
        )

        assert len(result) == 1
        assert result[0].amount_sold is None

    @patch("apps.agents.sources.sec_form_d.time.sleep")
    def test_rate_limiting_between_requests(
        self, mock_sleep: MagicMock
    ) -> None:
        """With 2 company names, time.sleep(0.1) is called between requests."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_sec_form_d(source, client, ["CompanyA", "CompanyB"])

        mock_sleep.assert_called_once_with(0.1)

    def test_parses_date_filed_correctly(self) -> None:
        """date_filed is parsed from the file_date field."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_SEC_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(
            source, client, ["Nu Holdings Ltd"]
        )

        assert len(result) == 1
        assert result[0].date_filed == date(2026, 1, 20)

    def test_handles_malformed_json_gracefully(self) -> None:
        """Malformed JSON response returns [] (graceful degradation)."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(source, client, ["Nubank"])

        assert result == []

    def test_multiple_company_names_searched(self) -> None:
        """Each company name triggers a separate HTTP request."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_sec_form_d(
            source, client, ["CompanyA", "CompanyB", "CompanyC"]
        )

        assert client.get.call_count == 3

        # Verify each call searched for the right company name
        for i, name in enumerate(["CompanyA", "CompanyB", "CompanyC"]):
            call_args = client.get.call_args_list[i]
            params = call_args[1]["params"]
            assert params["q"] == name
            assert params["forms"] == "D"

    def test_source_url_constructed_correctly(self) -> None:
        """source_url is built from the CIK in the filing."""
        source = self._make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_SEC_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_sec_form_d(
            source, client, ["Nu Holdings Ltd"]
        )

        assert len(result) == 1
        expected_url = (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            "?action=getcompany&CIK=0001234567&type=D"
            "&dateb=&owner=include&count=10"
        )
        assert result[0].source_url == expected_url
