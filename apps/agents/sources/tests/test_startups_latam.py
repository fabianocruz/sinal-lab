"""Tests for StartupsLatam.com collector."""

from unittest.mock import MagicMock

import httpx
import pytest

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.startups_latam import (
    INDUSTRY_ALIASES,
    StartupsLatamCompany,
    _detect_country,
    _parse_startup,
    _strip_html,
    fetch_industries,
    fetch_startups_latam,
)


def _source() -> DataSourceConfig:
    return DataSourceConfig(
        name="startups_latam",
        source_type="api",
        url="https://startupslatam.com/wp-json/wp/v2/startup",
    )


def _industry_map():
    return {
        158: "Financial Technology/FinTech",
        160: "Artificial Intelligence and Machine Learning",
        167: "Healthcare/Medical Technology",
        153: "Retail and E-commerce",
        172: "Transportation and Logistics",
    }


def _wp_startup(name, slug=None, description="", industry_ids=None,
                content="", wp_id=1):
    """Build a WP startup JSON item."""
    return {
        "id": wp_id,
        "slug": slug or name.lower().replace(" ", "-"),
        "title": {"rendered": name},
        "content": {"rendered": f"<p>{content}</p>" if content else ""},
        "industry": industry_ids or [],
        "link": f"https://startupslatam.com/startup/{slug or name.lower().replace(' ', '-')}/",
        "yoast_head_json": {
            "description": description,
        },
    }


def _mock_client(get_responses=None, get_side_effect=None, total_pages=1):
    """Create a mock httpx.Client with configurable get() responses."""
    client = MagicMock(spec=httpx.Client)

    if get_side_effect:
        client.get.side_effect = get_side_effect
        return client

    if get_responses is None:
        get_responses = []

    if isinstance(get_responses, list):
        mock_responses = []
        for i, resp_data in enumerate(get_responses):
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.status_code = 200
            mock_resp.json.return_value = resp_data
            mock_resp.raise_for_status.return_value = None
            mock_resp.headers = {"X-WP-TotalPages": str(total_pages)}
            mock_responses.append(mock_resp)
        client.get.side_effect = mock_responses
    else:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = get_responses
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"X-WP-TotalPages": str(total_pages)}
        client.get.return_value = mock_resp

    return client


# --- _strip_html tests ---


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_plain_text_unchanged(self):
        assert _strip_html("No HTML here") == "No HTML here"

    def test_nested_tags(self):
        result = _strip_html("<div><p>Nested <span>content</span></p></div>")
        assert "Nested content" in result


# --- _detect_country tests ---


class TestDetectCountry:
    def test_chilean_adjective(self):
        assert _detect_country("Examedi es una startup chilena fundada en Santiago") == "Chile"

    def test_mexican_adjective(self):
        assert _detect_country("Es una empresa mexicana de tecnología") == "Mexico"

    def test_brazilian_adjective(self):
        assert _detect_country("Startup brasileira de fintech") == "Brazil"

    def test_colombian_adjective(self):
        assert _detect_country("Empresa colombiana de pagamentos") == "Colombia"

    def test_argentine_adjective(self):
        assert _detect_country("Startup argentina de educación") == "Argentina"

    def test_peruvian_adjective(self):
        assert _detect_country("Startup peruana enfocada en transporte") == "Peru"

    def test_direct_country_mention(self):
        assert _detect_country("Fundada en Chile en 2020") == "Chile"

    def test_mexico_with_accent(self):
        assert _detect_country("Fundada en México por dos ingenieros") == "Mexico"

    def test_brasil_direct(self):
        assert _detect_country("Con sede en Brasil, la compañía") == "Brazil"

    def test_empty_returns_empty(self):
        assert _detect_country("") == ""

    def test_no_country_returns_empty(self):
        assert _detect_country("A technology company building AI solutions") == ""

    def test_uses_first_500_chars(self):
        # Country in first 500 chars should be found
        text = "Startup chilena " + "x" * 600
        assert _detect_country(text) == "Chile"

    def test_country_beyond_500_chars_not_detected(self):
        # Country after 500 chars should NOT be found
        text = "x" * 510 + " startup chilena"
        assert _detect_country(text) == ""


# --- _parse_startup tests ---


class TestParseStartup:
    def test_basic_parsing(self):
        item = _wp_startup("Examedi", "examedi", description="A health startup",
                           industry_ids=[167], content="Startup chilena de salud")
        result = _parse_startup(item, _industry_map())
        assert result is not None
        assert result.name == "Examedi"
        assert result.slug == "examedi"
        assert result.industry == "Healthcare/Medical Technology"
        assert result.country == "Chile"
        assert result.description == "A health startup"

    def test_skips_empty_name(self):
        item = _wp_startup("", "no-name")
        assert _parse_startup(item, _industry_map()) is None

    def test_falls_back_to_content_for_description(self):
        item = _wp_startup("Test", "test", content="Content description here")
        result = _parse_startup(item, {})
        assert "Content description here" in result.description

    def test_truncates_long_description(self):
        long_desc = "x" * 600
        item = _wp_startup("Test", "test", description=long_desc)
        result = _parse_startup(item, {})
        assert len(result.description) <= 500
        assert result.description.endswith("...")

    def test_unknown_industry_id(self):
        item = _wp_startup("Test", "test", industry_ids=[9999])
        result = _parse_startup(item, _industry_map())
        assert result.industry == ""

    def test_multiple_industry_ids_uses_first(self):
        item = _wp_startup("Test", "test", industry_ids=[158, 160])
        result = _parse_startup(item, _industry_map())
        assert result.industry == "Financial Technology/FinTech"

    def test_generates_source_url(self):
        item = _wp_startup("Test", "test")
        item["link"] = "https://startupslatam.com/startup/test/"
        result = _parse_startup(item, {})
        assert result.source_url == "https://startupslatam.com/startup/test/"

    def test_country_from_description_fallback(self):
        item = _wp_startup("Test", "test", description="Empresa mexicana de AI")
        result = _parse_startup(item, {})
        assert result.country == "Mexico"

    def test_html_stripped_from_title(self):
        item = _wp_startup("Test <b>Corp</b>", "test")
        item["title"]["rendered"] = "Test <b>Corp</b>"
        result = _parse_startup(item, {})
        assert result.name == "Test Corp"

    def test_stores_industry_ids(self):
        item = _wp_startup("Test", "test", industry_ids=[158, 160])
        result = _parse_startup(item, _industry_map())
        assert result.industry_ids == [158, 160]


# --- fetch_industries tests ---


class TestFetchIndustries:
    def test_parses_industries(self):
        data = [
            {"id": 158, "name": "Financial Technology/FinTech", "count": 91},
            {"id": 160, "name": "Artificial Intelligence and Machine Learning", "count": 53},
        ]
        # Wrap in list so mock returns the full list as a single response
        client = _mock_client(get_responses=[data])
        result = fetch_industries(client)
        assert result == {158: "Financial Technology/FinTech", 160: "Artificial Intelligence and Machine Learning"}

    def test_handles_timeout(self):
        client = _mock_client(get_side_effect=httpx.TimeoutException("timeout"))
        result = fetch_industries(client)
        assert result == {}

    def test_handles_http_error(self):
        client = _mock_client(get_side_effect=httpx.HTTPError("500"))
        result = fetch_industries(client)
        assert result == {}

    def test_empty_response(self):
        client = _mock_client(get_responses=[])
        result = fetch_industries(client)
        assert result == {}


# --- fetch_startups_latam tests ---


class TestFetchStartupsLatam:
    def test_fetches_single_page(self):
        industries = [
            {"id": 158, "name": "Financial Technology/FinTech", "count": 1},
        ]
        startups = [
            _wp_startup("Neon", "neon", description="A fintech",
                        industry_ids=[158], content="Startup brasileira"),
            _wp_startup("Rappi", "rappi", description="Delivery",
                        content="Empresa colombiana"),
        ]
        client = _mock_client(get_responses=[industries, startups], total_pages=1)
        result = fetch_startups_latam(_source(), client)
        assert len(result) == 2
        assert result[0].name == "Neon"
        assert result[0].country == "Brazil"
        assert result[1].name == "Rappi"
        assert result[1].country == "Colombia"

    def test_paginates_multiple_pages(self):
        industries = [{"id": 158, "name": "FinTech", "count": 2}]
        page1 = [_wp_startup("A", "a", content="Startup chilena")]
        page2 = [_wp_startup("B", "b", content="Startup mexicana")]
        client = _mock_client(get_responses=[industries, page1, page2], total_pages=2)
        result = fetch_startups_latam(_source(), client)
        assert len(result) == 2

    def test_handles_timeout_on_page(self):
        industries = [{"id": 1, "name": "Tech", "count": 1}]
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = industries
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"X-WP-TotalPages": "1"}

        client = MagicMock(spec=httpx.Client)
        client.get.side_effect = [mock_resp, httpx.TimeoutException("timeout")]

        result = fetch_startups_latam(_source(), client)
        assert result == []

    def test_skips_entries_without_name(self):
        industries = []
        startups = [
            _wp_startup("", "no-name"),
            _wp_startup("Valid", "valid"),
        ]
        client = _mock_client(get_responses=[industries, startups], total_pages=1)
        result = fetch_startups_latam(_source(), client)
        assert len(result) == 1
        assert result[0].name == "Valid"

    def test_empty_startup_list(self):
        industries = []
        startups = []
        client = _mock_client(get_responses=[industries, startups], total_pages=1)
        result = fetch_startups_latam(_source(), client)
        assert result == []

    def test_uses_source_url(self):
        """Uses URL from DataSourceConfig if provided."""
        source = DataSourceConfig(
            name="startups_latam",
            source_type="api",
            url="https://custom-url.com/api/startups",
        )
        industries = []
        startups = [_wp_startup("Test", "test")]
        client = _mock_client(get_responses=[industries, startups], total_pages=1)
        result = fetch_startups_latam(source, client)
        assert len(result) == 1
        # Verify it used the custom URL
        calls = client.get.call_args_list
        # Second call (after industries) should use source URL
        assert "custom-url.com" in str(calls[1])


# --- Industry alias mapping tests ---


class TestIndustryAliases:
    def test_all_aliases_are_strings(self):
        for key, value in INDUSTRY_ALIASES.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_fintech_mapping(self):
        assert INDUSTRY_ALIASES["Financial Technology/FinTech"] == "Fintech"

    def test_ai_mapping(self):
        assert INDUSTRY_ALIASES["Artificial Intelligence and Machine Learning"] == "artificial intelligence"

    def test_healthcare_mapping(self):
        assert INDUSTRY_ALIASES["Healthcare/Medical Technology"] == "healthcare"

    def test_ecommerce_mapping(self):
        assert INDUSTRY_ALIASES["Retail and E-commerce"] == "ecommerce"


# --- Integration-style test ---


class TestEndToEnd:
    def test_full_pipeline_mock(self):
        """Test the full fetch flow with realistic mock data."""
        industries = [
            {"id": 158, "name": "Financial Technology/FinTech", "count": 91},
            {"id": 167, "name": "Healthcare/Medical Technology", "count": 29},
        ]
        startups = [
            {
                "id": 100,
                "slug": "examedi",
                "title": {"rendered": "Examedi"},
                "content": {"rendered": "<p>Examedi es una startup chilena fundada con el objetivo de transformar la salud</p>"},
                "industry": [167],
                "link": "https://startupslatam.com/startup/examedi/",
                "yoast_head_json": {
                    "description": "Transformar el acceso a la atención médica en América Latina",
                },
            },
            {
                "id": 200,
                "slug": "clip",
                "title": {"rendered": "Clip"},
                "content": {"rendered": "<p>Clip es una empresa mexicana de pagos digitales</p>"},
                "industry": [158],
                "link": "https://startupslatam.com/startup/clip/",
                "yoast_head_json": {
                    "description": "Pagos digitales en México",
                },
            },
        ]
        client = _mock_client(get_responses=[industries, startups], total_pages=1)
        result = fetch_startups_latam(_source(), client)

        assert len(result) == 2

        examedi = result[0]
        assert examedi.name == "Examedi"
        assert examedi.country == "Chile"
        assert examedi.industry == "Healthcare/Medical Technology"
        assert "atención médica" in examedi.description

        clip = result[1]
        assert clip.name == "Clip"
        assert clip.country == "Mexico"
        assert clip.industry == "Financial Technology/FinTech"
