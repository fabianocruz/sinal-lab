"""Tests for MERCADO agent collector."""

import pytest
from unittest.mock import Mock, patch

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.mercado.collector import (
    CompanyProfile,
    collect_from_github,
    collect_all_sources,
    is_likely_startup,
)


@pytest.fixture
def mock_github_response():
    """Mock GitHub Search Users API response (organizations)."""
    return {
        "total_count": 2,
        "items": [
            {
                "login": "nubank",
                "html_url": "https://github.com/nubank",
                "type": "Organization",
                "description": "Functional machine learning",
            },
            {
                "login": "stone-payments",
                "html_url": "https://github.com/stone-payments",
                "type": "Organization",
                "description": "Microservice gateway",
            },
        ],
    }


@pytest.fixture
def github_source():
    """GitHub API data source configuration."""
    return DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/users",
        enabled=True,
        params={"q": 'location:"São Paulo" type:org repos:>5', "sort": "repositories", "per_page": 100},
    )


@pytest.fixture
def provenance():
    """Provenance tracker."""
    return ProvenanceTracker()


@patch("httpx.get")
def test_collect_from_github_success(mock_get, mock_github_response, github_source, provenance):
    """Test collecting company profiles from GitHub API."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_github_response
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profiles = collect_from_github(github_source, provenance)

    assert len(profiles) == 2
    assert profiles[0].name == "Nubank"
    assert profiles[0].slug == "nubank"
    assert profiles[0].city == "São Paulo"
    assert profiles[0].country == "Brasil"
    assert profiles[0].github_url == "https://github.com/nubank"
    assert profiles[1].name == "Stone Payments"


@patch("httpx.get")
def test_collect_from_github_timeout(mock_get, github_source, provenance):
    """Test handling GitHub API timeout."""
    import httpx

    mock_get.side_effect = httpx.TimeoutException("Timeout")

    profiles = collect_from_github(github_source, provenance)

    assert profiles == []


@patch("httpx.get")
def test_collect_from_github_http_error(mock_get, github_source, provenance):
    """Test handling GitHub API HTTP error."""
    import httpx

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=Mock(), response=Mock()
    )
    mock_get.return_value = mock_response

    profiles = collect_from_github(github_source, provenance)

    assert profiles == []


@patch("httpx.get")
def test_collect_from_github_skips_items_without_login(mock_get, github_source, provenance):
    """Test that items without a login are skipped."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "total_count": 2,
        "items": [
            {
                "login": "",  # Empty login, should be skipped
                "html_url": "https://github.com/ghost",
                "type": "Organization",
            },
            {
                "login": "acme-corp",
                "html_url": "https://github.com/acme-corp",
                "type": "Organization",
                "description": "Corporate app",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profiles = collect_from_github(github_source, provenance)

    assert len(profiles) == 1
    assert profiles[0].name == "Acme Corp"


def test_collect_all_sources_skips_disabled(provenance):
    """Test that disabled sources are skipped."""
    sources = [
        DataSourceConfig(
            name="github_test",
            source_type="api",
            url="https://api.github.com/search/users",
            enabled=False,  # Disabled
        ),
    ]

    profiles = collect_all_sources(sources, provenance)

    assert profiles == []


@patch("apps.agents.mercado.collector.collect_from_github")
def test_collect_all_sources_multiple(mock_collect_github, provenance):
    """Test collecting from multiple GitHub sources."""
    mock_collect_github.return_value = [
        CompanyProfile(
            name="Company A",
            slug="company-a",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/company-a",
            source_name="github_sao_paulo",
        ),
    ]

    sources = [
        DataSourceConfig(
            name="github_sao_paulo",
            source_type="api",
            url="https://api.github.com/search/users",
            enabled=True,
        ),
        DataSourceConfig(
            name="github_rio",
            source_type="api",
            url="https://api.github.com/search/users",
            enabled=True,
        ),
    ]

    profiles = collect_all_sources(sources, provenance)

    # Should call GitHub collector twice
    assert mock_collect_github.call_count == 2
    assert len(profiles) == 2


class TestIsLikelyStartup:
    """Test non-startup filtering logic."""

    def test_filters_university_by_login(self):
        assert not is_likely_startup("FIAP", "")

    def test_filters_university_by_description(self):
        assert not is_likely_startup("some-org", "Universidade de São Paulo")

    def test_filters_government(self):
        assert not is_likely_startup("prefeiturasp", "")

    def test_filters_training_platform(self):
        assert not is_likely_startup("treinaweb", "")

    def test_filters_course_provider(self):
        assert not is_likely_startup("curso-r", "R courses for data science")

    def test_filters_alura(self):
        assert not is_likely_startup("alura-es-cursos", "")

    def test_filters_fatec(self):
        assert not is_likely_startup("FatecFranca", "")

    def test_filters_archive(self):
        assert not is_likely_startup("alexfalcucci-archive", "")

    def test_allows_real_startup(self):
        assert is_likely_startup("nubank", "Functional machine learning")

    def test_allows_tech_company(self):
        assert is_likely_startup("stone-payments", "Microservice gateway")

    def test_filters_known_large_company_vtex(self):
        assert not is_likely_startup("vtex", "")

    def test_filters_known_large_company_vtex_apps(self):
        assert not is_likely_startup("vtex-apps", "")

    def test_filters_platzi(self):
        assert not is_likely_startup("PlatziMaster", "Learning platform")

    def test_filters_school(self):
        assert not is_likely_startup("tech-school", "")

    def test_filters_gov(self):
        assert not is_likely_startup("gov-digital", "Government digital services")

    # --- Known large companies ---
    def test_filters_globocom(self):
        assert not is_likely_startup("globocom", "")

    def test_filters_wizeline(self):
        assert not is_likely_startup("wizeline", "Open source projects")

    def test_filters_mercadolibre(self):
        assert not is_likely_startup("mercadolibre", "")

    def test_filters_totvs(self):
        assert not is_likely_startup("totvs", "")

    # --- Academic/research groups ---
    def test_filters_software_design_lab(self):
        assert not is_likely_startup("TheSoftwareDesignLab", "Software engineering research")

    def test_filters_university_chapter(self):
        assert not is_likely_startup("CapituloJaverianoACM", "")

    def test_filters_udistrital(self):
        assert not is_likely_startup("Udistrital", "")

    def test_filters_uspgamedev(self):
        assert not is_likely_startup("uspgamedev", "")

    def test_filters_thunderatz(self):
        assert not is_likely_startup("ThundeRatz", "USP robotics team")

    # --- Non-profits/NGOs ---
    def test_filters_bireme(self):
        assert not is_likely_startup("bireme", "PAHO/WHO")

    def test_filters_hacklabr(self):
        assert not is_likely_startup("hacklabr", "")

    # --- Personal accounts ---
    def test_filters_personal_eti(self):
        assert not is_likely_startup("thiagobruno-eti", "")

    def test_filters_geosaber(self):
        assert not is_likely_startup("geosaber", "")

    # --- False positive safety: real startups must still pass ---
    def test_allows_entria(self):
        assert is_likely_startup("entria", "")

    def test_allows_cloudwalk(self):
        assert is_likely_startup("cloudwalk-inc", "Payments infrastructure")

    def test_allows_nuvemshop(self):
        assert is_likely_startup("nuvemshop", "E-commerce platform for LATAM")

    def test_allows_creditas(self):
        assert is_likely_startup("creditas", "")

    def test_allows_loft(self):
        assert is_likely_startup("loft-br", "Real estate platform")

    # --- Government (Spanish) ---
    def test_filters_gobierno(self):
        assert not is_likely_startup("gobierno-digital", "")

    def test_filters_municipio(self):
        assert not is_likely_startup("municipio-mx", "Servicios municipales")


@patch("httpx.get")
def test_collect_from_github_filters_non_startups(mock_get, github_source, provenance):
    """Test that non-startup organizations are filtered out."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "total_count": 4,
        "items": [
            {
                "login": "nubank",
                "html_url": "https://github.com/nubank",
                "type": "Organization",
                "description": "Functional machine learning",
            },
            {
                "login": "prefeiturasp",
                "html_url": "https://github.com/prefeiturasp",
                "type": "Organization",
                "description": "Prefeitura de São Paulo",
            },
            {
                "login": "FIAP",
                "html_url": "https://github.com/FIAP",
                "type": "Organization",
                "description": "Faculdade de Informática",
            },
            {
                "login": "stone-payments",
                "html_url": "https://github.com/stone-payments",
                "type": "Organization",
                "description": "Payment platform",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profiles = collect_from_github(github_source, provenance)

    assert len(profiles) == 2
    names = [p.name for p in profiles]
    assert "Nubank" in names
    assert "Stone Payments" in names


# --- BCB Integration Tests ---


@patch("apps.agents.sources.bcb_institutions.fetch_bcb_institutions")
def test_bcb_institutions_converted_to_profiles(mock_fetch_bcb, provenance):
    """BCB institutions are converted to CompanyProfile objects."""
    from apps.agents.sources.bcb_institutions import BCBInstitution

    mock_fetch_bcb.return_value = [
        BCBInstitution(
            name="Nubank S.A.",
            cnpj="18.236.120/0001-58",
            segment="b4",
            situation="Autorizada",
            municipality="São Paulo",
            state="SP",
        ),
    ]

    sources = [
        DataSourceConfig(
            name="bcb_authorized",
            source_type="api",
            url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
            params={"segments": "b4"},
        ),
    ]

    profiles = collect_all_sources(sources, provenance)

    assert len(profiles) == 1
    assert profiles[0].name == "Nubank S.A."
    assert profiles[0].sector == "Fintech"
    assert profiles[0].source_name == "bcb_authorized"
    assert profiles[0].city == "São Paulo"


def test_bcb_skipped_when_disabled(provenance):
    """No BCB calls when source is disabled."""
    sources = [
        DataSourceConfig(
            name="bcb_authorized",
            source_type="api",
            url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
            enabled=False,
        ),
    ]

    profiles = collect_all_sources(sources, provenance)
    assert profiles == []


@patch("apps.agents.sources.bcb_institutions.fetch_bcb_institutions")
def test_bcb_graceful_degradation(mock_fetch_bcb, provenance):
    """BCB API failure doesn't break collection from other sources."""
    mock_fetch_bcb.side_effect = Exception("BCB API down")

    sources = [
        DataSourceConfig(
            name="bcb_authorized",
            source_type="api",
            url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
            params={"segments": "b4"},
        ),
    ]

    # Should not raise
    profiles = collect_all_sources(sources, provenance)
    assert profiles == []


@patch("apps.agents.sources.bcb_institutions.fetch_bcb_institutions")
def test_bcb_profiles_have_correct_tags(mock_fetch_bcb, provenance):
    """BCB profiles have segment and bcb-authorized tags."""
    from apps.agents.sources.bcb_institutions import BCBInstitution

    mock_fetch_bcb.return_value = [
        BCBInstitution(
            name="PagBank",
            cnpj="08.561.701/0001-01",
            segment="b4",
            situation="Autorizada",
        ),
    ]

    sources = [
        DataSourceConfig(
            name="bcb_authorized",
            source_type="api",
            url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
            params={"segments": "b4"},
        ),
    ]

    profiles = collect_all_sources(sources, provenance)

    assert "b4" in profiles[0].tags
    assert "bcb-authorized" in profiles[0].tags


@patch("apps.agents.sources.bcb_institutions.fetch_bcb_institutions")
def test_bcb_slug_from_cnpj(mock_fetch_bcb, provenance):
    """BCB profile slug is normalized CNPJ (digits only)."""
    from apps.agents.sources.bcb_institutions import BCBInstitution

    mock_fetch_bcb.return_value = [
        BCBInstitution(
            name="TestBank",
            cnpj="12.345.678/0001-90",
            segment="b1",
            situation="Autorizada",
        ),
    ]

    sources = [
        DataSourceConfig(
            name="bcb_authorized",
            source_type="api",
            url="https://olinda.bcb.gov.br/olinda/servico/DASFN/versao/v1/odata/IfDataDes662",
            params={"segments": "b1"},
        ),
    ]

    profiles = collect_all_sources(sources, provenance)
    assert profiles[0].slug == "12345678000190"


# --- Gupy Enrichment Tests ---


@patch("apps.agents.sources.gupy_jobs.fetch_gupy_jobs")
def test_enrich_from_gupy_adds_tech_stack(mock_fetch_gupy):
    """Gupy enrichment adds tech_stack to matching profiles."""
    from apps.agents.sources.gupy_jobs import GupyJobListing
    from apps.agents.mercado.collector import enrich_from_gupy

    mock_fetch_gupy.return_value = [
        GupyJobListing(
            company_slug="nubank",
            role_title="Backend Engineer",
            url="https://nubank.gupy.io/job/123",
            tech_stack=["Python", "Kafka"],
        ),
    ]

    profiles = [
        CompanyProfile(
            name="Nubank",
            slug="nubank",
            source_url="https://github.com/nubank",
            source_name="github_sao_paulo",
        ),
    ]

    gupy_source = DataSourceConfig(name="gupy_jobs", source_type="api", url=None, params={"max_slugs": 20})
    result = enrich_from_gupy(profiles, gupy_source)

    assert "Python" in result[0].tech_stack
    assert "Kafka" in result[0].tech_stack


@patch("apps.agents.sources.gupy_jobs.fetch_gupy_jobs")
def test_enrich_from_gupy_no_match(mock_fetch_gupy):
    """Profiles with no Gupy match keep existing tech_stack."""
    mock_fetch_gupy.return_value = []  # No jobs found

    from apps.agents.mercado.collector import enrich_from_gupy

    profiles = [
        CompanyProfile(
            name="Unknown Co",
            slug="unknown-co",
            tech_stack=["React"],
            source_url="https://github.com/unknown",
            source_name="github_sao_paulo",
        ),
    ]

    gupy_source = DataSourceConfig(name="gupy_jobs", source_type="api", url=None, params={"max_slugs": 20})
    result = enrich_from_gupy(profiles, gupy_source)

    assert result[0].tech_stack == ["React"]


@patch("apps.agents.sources.gupy_jobs.fetch_gupy_jobs")
def test_enrich_from_gupy_graceful_degradation(mock_fetch_gupy):
    """Gupy API failure returns profiles unchanged."""
    from apps.agents.mercado.collector import enrich_from_gupy

    mock_fetch_gupy.side_effect = Exception("Gupy API down")

    profiles = [
        CompanyProfile(
            name="TestCo",
            slug="testco",
            tech_stack=["Python"],
            source_url="https://github.com/testco",
            source_name="github_sao_paulo",
        ),
    ]

    gupy_source = DataSourceConfig(name="gupy_jobs", source_type="api", url=None, params={"max_slugs": 20})
    result = enrich_from_gupy(profiles, gupy_source)

    assert result[0].tech_stack == ["Python"]


def test_enrich_from_gupy_empty_profiles():
    """Empty profile list returns empty."""
    from apps.agents.mercado.collector import enrich_from_gupy

    gupy_source = DataSourceConfig(name="gupy_jobs", source_type="api", url=None, params={"max_slugs": 20})
    result = enrich_from_gupy([], gupy_source)
    assert result == []


@patch("apps.agents.sources.gupy_jobs.fetch_gupy_jobs")
def test_enrich_from_gupy_merges_tech_stacks(mock_fetch_gupy):
    """Gupy tech_stack merges with existing (union, not replace)."""
    from apps.agents.sources.gupy_jobs import GupyJobListing
    from apps.agents.mercado.collector import enrich_from_gupy

    mock_fetch_gupy.return_value = [
        GupyJobListing(
            company_slug="testco",
            role_title="Full Stack Dev",
            url="https://testco.gupy.io/job/456",
            tech_stack=["React", "Docker"],
        ),
    ]

    profiles = [
        CompanyProfile(
            name="TestCo",
            slug="testco",
            tech_stack=["Python", "React"],  # React is already there
            source_url="https://github.com/testco",
            source_name="github_sao_paulo",
        ),
    ]

    gupy_source = DataSourceConfig(name="gupy_jobs", source_type="api", url=None, params={"max_slugs": 20})
    result = enrich_from_gupy(profiles, gupy_source)

    assert "Python" in result[0].tech_stack
    assert "React" in result[0].tech_stack
    assert "Docker" in result[0].tech_stack
    assert len(result[0].tech_stack) == 3  # No duplicates
