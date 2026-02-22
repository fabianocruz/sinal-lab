"""Tests for BCB (Banco Central do Brasil) institutions source module.

Tests BCBInstitution dataclass, _normalize_cnpj helper, fetch_bcb_institutions
function (with OData pagination), and detect_new_authorizations comparator.
"""

import hashlib
from unittest.mock import MagicMock, call

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.bcb_institutions import (
    BCB_ODATA_BASE,
    BCBInstitution,
    _normalize_cnpj,
    detect_new_authorizations,
    fetch_bcb_institutions,
)
from apps.agents.sources.verification import SourceAuthority, VerificationLevel

# ---------------------------------------------------------------------------
# Sample mock data
# ---------------------------------------------------------------------------

SAMPLE_BCB_RESPONSE = {
    "value": [
        {
            "Nome": "NU PAGAMENTOS S.A.",
            "Cnpj": "18.236.120/0001-58",
            "Segmento": "b4",
            "DtAutorizacao": "2017-09-15",
            "Situacao": "Autorizada",
            "Municipio": "SAO PAULO",
            "UF": "SP",
        },
        {
            "Nome": "CREDITAS SOCIEDADE DE CREDITO",
            "Cnpj": "32.876.929/0001-82",
            "Segmento": "b2",
            "DtAutorizacao": "2019-03-22",
            "Situacao": "Autorizada",
            "Municipio": "SAO PAULO",
            "UF": "SP",
        },
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(name: str = "bcb_institutions") -> DataSourceConfig:
    """Helper to create a DataSourceConfig for BCB institutions."""
    return DataSourceConfig(
        name=name,
        source_type="api",
        url=BCB_ODATA_BASE,
    )


# ---------------------------------------------------------------------------
# TestNormalizeCnpj
# ---------------------------------------------------------------------------


class TestNormalizeCnpj:
    """Test _normalize_cnpj helper function."""

    def test_strips_punctuation(self) -> None:
        """Formatted CNPJ is stripped to digits only."""
        assert _normalize_cnpj("12.345.678/0001-90") == "12345678000190"

    def test_already_clean(self) -> None:
        """Already-clean CNPJ passes through unchanged."""
        assert _normalize_cnpj("12345678000190") == "12345678000190"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert _normalize_cnpj("") == ""


# ---------------------------------------------------------------------------
# TestBCBInstitution
# ---------------------------------------------------------------------------


class TestBCBInstitution:
    """Test BCBInstitution dataclass initialization and auto-computed fields."""

    def test_content_hash_from_normalized_cnpj(self) -> None:
        """content_hash is MD5 of digits-only CNPJ."""
        inst = BCBInstitution(
            name="NU PAGAMENTOS S.A.",
            cnpj="18.236.120/0001-58",
            segment="b4",
            situation="Autorizada",
        )
        expected_hash = hashlib.md5("18236120000158".encode()).hexdigest()
        assert inst.content_hash == expected_hash

    def test_authority_auto_created(self) -> None:
        """Authority is auto-created with REGULATORY level and BCB institution."""
        inst = BCBInstitution(
            name="TEST BANK",
            cnpj="00000000000100",
            segment="b1",
            situation="Autorizada",
        )
        assert inst.authority is not None
        assert inst.authority.verification_level == VerificationLevel.REGULATORY
        assert inst.authority.institution_name == "BCB"

    def test_all_fields_populated(self) -> None:
        """All fields are stored correctly when fully provided."""
        inst = BCBInstitution(
            name="NU PAGAMENTOS S.A.",
            cnpj="18.236.120/0001-58",
            segment="b4",
            situation="Autorizada",
            authorization_date="2017-09-15",
            municipality="SAO PAULO",
            state="SP",
        )

        assert inst.name == "NU PAGAMENTOS S.A."
        assert inst.cnpj == "18.236.120/0001-58"
        assert inst.segment == "b4"
        assert inst.situation == "Autorizada"
        assert inst.authorization_date == "2017-09-15"
        assert inst.municipality == "SAO PAULO"
        assert inst.state == "SP"
        assert inst.content_hash != ""
        assert inst.authority is not None

    def test_custom_content_hash_not_overwritten(self) -> None:
        """Provided content_hash is preserved, not auto-computed."""
        custom_hash = "my_custom_hash_abc123"
        inst = BCBInstitution(
            name="TEST BANK",
            cnpj="00000000000100",
            segment="b1",
            situation="Autorizada",
            content_hash=custom_hash,
        )
        assert inst.content_hash == custom_hash


# ---------------------------------------------------------------------------
# TestFetchBcbInstitutions
# ---------------------------------------------------------------------------


class TestFetchBcbInstitutions:
    """Test fetch_bcb_institutions function."""

    def test_successful_fetch(self) -> None:
        """Successful API call returns parsed BCBInstitution objects."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_BCB_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_bcb_institutions(source, client)

        assert len(result) == 2
        assert all(isinstance(inst, BCBInstitution) for inst in result)

        # First institution
        assert result[0].name == "NU PAGAMENTOS S.A."
        assert result[0].cnpj == "18.236.120/0001-58"
        assert result[0].segment == "b4"
        assert result[0].authorization_date == "2017-09-15"
        assert result[0].situation == "Autorizada"
        assert result[0].municipality == "SAO PAULO"
        assert result[0].state == "SP"

        # Second institution
        assert result[1].name == "CREDITAS SOCIEDADE DE CREDITO"
        assert result[1].cnpj == "32.876.929/0001-82"
        assert result[1].segment == "b2"

    def test_returns_empty_list_on_http_error(self) -> None:
        """HTTP error during API call returns []."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("API error")

        result = fetch_bcb_institutions(source, client)

        assert result == []

    def test_returns_empty_list_on_timeout(self) -> None:
        """Timeout during API call returns []."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.TimeoutException("Request timeout")

        result = fetch_bcb_institutions(source, client)

        assert result == []

    def test_handles_odata_pagination(self) -> None:
        """Follows @odata.nextLink to collect all pages."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        page_1_response = MagicMock()
        page_1_response.json.return_value = {
            "value": [
                {
                    "Nome": "BANCO ALPHA S.A.",
                    "Cnpj": "11.111.111/0001-11",
                    "Segmento": "b1",
                    "DtAutorizacao": "2020-01-01",
                    "Situacao": "Autorizada",
                    "Municipio": "BRASILIA",
                    "UF": "DF",
                },
            ],
            "@odata.nextLink": "https://olinda.bcb.gov.br/next-page?skip=1",
        }
        page_1_response.raise_for_status = MagicMock()

        page_2_response = MagicMock()
        page_2_response.json.return_value = {
            "value": [
                {
                    "Nome": "BANCO BETA S.A.",
                    "Cnpj": "22.222.222/0001-22",
                    "Segmento": "b2",
                    "DtAutorizacao": "2021-06-15",
                    "Situacao": "Autorizada",
                    "Municipio": "RIO DE JANEIRO",
                    "UF": "RJ",
                },
            ],
        }
        page_2_response.raise_for_status = MagicMock()

        client.get.side_effect = [page_1_response, page_2_response]

        result = fetch_bcb_institutions(source, client)

        assert len(result) == 2
        assert result[0].name == "BANCO ALPHA S.A."
        assert result[1].name == "BANCO BETA S.A."

        # Verify two GET calls were made
        assert client.get.call_count == 2

    def test_segment_filter_applied(self) -> None:
        """When segments are provided, $filter param is included in request."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        fetch_bcb_institutions(source, client, segments=["b1"])

        call_args = client.get.call_args
        params = call_args[1]["params"]
        assert "$filter" in params
        assert params["$filter"] == "Segmento eq 'b1'"

    def test_handles_malformed_json_gracefully(self) -> None:
        """Malformed JSON response returns []."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_bcb_institutions(source, client)

        assert result == []


# ---------------------------------------------------------------------------
# TestDetectNewAuthorizations
# ---------------------------------------------------------------------------


class TestDetectNewAuthorizations:
    """Test detect_new_authorizations comparison function."""

    def test_detects_new_institutions(self) -> None:
        """Institutions in current but not in previous are returned."""
        current = [
            BCBInstitution(
                name="BANCO A",
                cnpj="11.111.111/0001-11",
                segment="b1",
                situation="Autorizada",
            ),
            BCBInstitution(
                name="BANCO B",
                cnpj="22.222.222/0001-22",
                segment="b2",
                situation="Autorizada",
            ),
            BCBInstitution(
                name="BANCO C",
                cnpj="33.333.333/0001-33",
                segment="b3",
                situation="Autorizada",
            ),
        ]
        previous = [
            BCBInstitution(
                name="BANCO A",
                cnpj="11111111000111",  # Same CNPJ, different format
                segment="b1",
                situation="Autorizada",
            ),
            BCBInstitution(
                name="BANCO B",
                cnpj="22.222.222/0001-22",
                segment="b2",
                situation="Autorizada",
            ),
        ]

        new = detect_new_authorizations(current, previous)

        assert len(new) == 1
        assert new[0].name == "BANCO C"
        assert new[0].cnpj == "33.333.333/0001-33"

    def test_no_new_institutions(self) -> None:
        """All current institutions exist in previous returns empty list."""
        current = [
            BCBInstitution(
                name="BANCO A",
                cnpj="11.111.111/0001-11",
                segment="b1",
                situation="Autorizada",
            ),
        ]
        previous = [
            BCBInstitution(
                name="BANCO A",
                cnpj="11111111000111",  # Same CNPJ, different format
                segment="b1",
                situation="Autorizada",
            ),
        ]

        new = detect_new_authorizations(current, previous)

        assert new == []

    def test_empty_previous_returns_all_current(self) -> None:
        """When previous is empty, all current institutions are new."""
        current = [
            BCBInstitution(
                name="BANCO A",
                cnpj="11.111.111/0001-11",
                segment="b1",
                situation="Autorizada",
            ),
            BCBInstitution(
                name="BANCO B",
                cnpj="22.222.222/0001-22",
                segment="b2",
                situation="Autorizada",
            ),
        ]

        new = detect_new_authorizations(current, previous=[])

        assert len(new) == 2
        assert new[0].name == "BANCO A"
        assert new[1].name == "BANCO B"
