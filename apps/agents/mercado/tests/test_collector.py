"""Tests for MERCADO agent collector."""

import pytest
from unittest.mock import Mock, patch

from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker
from apps.agents.mercado.collector import (
    CompanyProfile,
    collect_from_github,
    collect_all_sources,
)


@pytest.fixture
def mock_github_response():
    """Mock GitHub Search API response."""
    return {
        "total_count": 2,
        "items": [
            {
                "owner": {
                    "login": "nubank",
                    "html_url": "https://github.com/nubank",
                    "type": "Organization",
                },
                "html_url": "https://github.com/nubank/fklearn",
                "description": "Functional machine learning",
                "language": "Python",
            },
            {
                "owner": {
                    "login": "stone-payments",
                    "html_url": "https://github.com/stone-payments",
                    "type": "Organization",
                },
                "html_url": "https://github.com/stone-payments/kong",
                "description": "Microservice gateway",
                "language": "Go",
            },
        ],
    }


@pytest.fixture
def github_source():
    """GitHub API data source configuration."""
    return DataSourceConfig(
        name="github_sao_paulo",
        source_type="api",
        url="https://api.github.com/search/repositories",
        enabled=True,
        params={"q": "location:São+Paulo stars:>100", "sort": "stars", "per_page": 100},
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
    assert profiles[0].name == "nubank"
    assert profiles[0].city == "São Paulo"
    assert profiles[0].country == "Brasil"
    assert "Python" in profiles[0].tech_stack
    assert profiles[1].name == "stone-payments"
    assert "Go" in profiles[1].tech_stack


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
def test_collect_from_github_filters_personal_repos(mock_get, github_source, provenance):
    """Test that personal (non-org) repos are filtered out."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "total_count": 2,
        "items": [
            {
                "owner": {
                    "login": "john-doe",
                    "html_url": "https://github.com/john-doe",
                    "type": "User",  # Personal account, should be filtered
                },
                "html_url": "https://github.com/john-doe/project",
                "description": "Personal project",
                "language": "Python",
            },
            {
                "owner": {
                    "login": "acme-corp",
                    "html_url": "https://github.com/acme-corp",
                    "type": "Organization",  # Should be included
                },
                "html_url": "https://github.com/acme-corp/app",
                "description": "Corporate app",
                "language": "JavaScript",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    profiles = collect_from_github(github_source, provenance)

    # Should only return the Organization repo
    assert len(profiles) == 1
    assert profiles[0].name == "acme-corp"


def test_collect_all_sources_skips_disabled(provenance):
    """Test that disabled sources are skipped."""
    sources = [
        DataSourceConfig(
            name="github_test",
            source_type="api",
            url="https://api.github.com/search/repositories",
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
            url="https://api.github.com/search/repositories",
            enabled=True,
        ),
        DataSourceConfig(
            name="github_rio",
            source_type="api",
            url="https://api.github.com/search/repositories",
            enabled=True,
        ),
    ]

    profiles = collect_all_sources(sources, provenance)

    # Should call GitHub collector twice
    assert mock_collect_github.call_count == 2
    assert len(profiles) == 2
