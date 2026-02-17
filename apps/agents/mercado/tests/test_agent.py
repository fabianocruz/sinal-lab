"""End-to-end tests for MERCADO agent."""

import pytest
from unittest.mock import patch, Mock

from apps.agents.mercado.agent import MercadoAgent
from apps.agents.mercado.collector import CompanyProfile


@pytest.fixture
def mercado_agent():
    """Create MercadoAgent instance for testing."""
    return MercadoAgent(week_number=7)


def test_agent_initialization(mercado_agent):
    """Test agent initialization."""
    assert mercado_agent.agent_name == "mercado"
    assert mercado_agent.week_number == 7
    assert mercado_agent.run_id.startswith("mercado-")


@patch("apps.agents.mercado.agent.collect_all_sources")
def test_collect_phase(mock_collect, mercado_agent):
    """Test collect phase returns CompanyProfile list."""
    # Mock collector to return sample profiles
    sample_profiles = [
        CompanyProfile(
            name="Nubank",
            slug="nubank",
            description="Digital bank",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/nubank",
            source_name="github_sao_paulo",
        ),
        CompanyProfile(
            name="Stone",
            slug="stone",
            description="Payment platform",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/stone",
            source_name="github_sao_paulo",
        ),
    ]
    mock_collect.return_value = sample_profiles

    result = mercado_agent.collect()

    assert len(result) == 2
    assert isinstance(result[0], CompanyProfile)
    assert mock_collect.called


def test_process_phase(mercado_agent):
    """Test process phase enriches and classifies profiles."""
    raw_profiles = [
        CompanyProfile(
            name="TestCo",
            slug="testco",
            description="Digital payment platform for SMBs",  # Should be classified as Fintech
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/testco",
            source_name="github_sao_paulo",
        ),
    ]

    processed = mercado_agent.process(raw_profiles)

    assert len(processed) > 0
    # Check classification happened
    assert processed[0].sector == "Fintech"
    # Check tags were generated
    assert len(processed[0].tags) > 0


def test_score_phase(mercado_agent):
    """Test score phase returns ScoredCompanyProfile list."""
    profiles = [
        CompanyProfile(
            name="TestCo",
            slug="testco",
            description="Test company",
            sector="SaaS",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/testco",
            source_name="github_sao_paulo",
        ),
    ]

    scores = mercado_agent.score(profiles)

    assert len(scores) > 0
    assert hasattr(scores[0], "confidence")
    assert hasattr(scores[0], "composite_score")


def test_output_phase(mercado_agent):
    """Test output phase generates AgentOutput."""
    profiles = [
        CompanyProfile(
            name="BigCorp",
            slug="bigcorp",
            description="Leading fintech platform",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            tech_stack=["Python", "React"],
            github_url="https://github.com/bigcorp",
            source_url="https://github.com/bigcorp",
            source_name="github_sao_paulo",
        ),
    ]

    scores = mercado_agent.score(profiles)
    output = mercado_agent.output(profiles, scores)

    assert output.title.startswith("MERCADO Report")
    assert "Semana 7" in output.title
    assert len(output.body_md) > 0
    assert output.agent_name == "mercado"
    assert output.content_type == "DATA_REPORT"


@patch("apps.agents.mercado.agent.collect_all_sources")
def test_full_agent_run(mock_collect, mercado_agent):
    """Test complete agent run end-to-end."""
    # Mock collector
    mock_collect.return_value = [
        CompanyProfile(
            name="TestStartup",
            slug="teststartup",
            description="Digital bank for entrepreneurs",
            city="São Paulo",
            country="Brasil",
            tech_stack=["Python", "Django"],
            github_url="https://github.com/teststartup",
            source_url="https://github.com/teststartup",
            source_name="github_sao_paulo",
        ),
    ]

    # Run agent
    result = mercado_agent.run()

    # Verify output
    assert result is not None
    assert result.title.startswith("MERCADO Report")
    assert "TestStartup" in result.body_md
    # Note: sources won't be tracked when using mocked collector
    assert result.confidence.composite > 0


def test_agent_run_with_no_profiles(mercado_agent):
    """Test agent run with empty profile list."""
    with patch("apps.agents.mercado.agent.collect_all_sources", return_value=[]):
        result = mercado_agent.run()

        # Should still produce output (empty report)
        assert result is not None
        assert len(result.body_md) > 0
        assert "Sem novas startups" in result.body_md


@patch("apps.agents.mercado.agent.collect_all_sources")
def test_agent_run_multiple_cities(mock_collect, mercado_agent):
    """Test agent run with profiles from multiple cities."""
    # Mock collector with profiles from different cities
    mock_collect.return_value = [
        CompanyProfile(
            name="SP Corp",
            slug="sp-corp",
            description="Fintech platform",
            sector="Fintech",
            city="São Paulo",
            country="Brasil",
            source_url="https://github.com/sp-corp",
            source_name="github_sao_paulo",
        ),
        CompanyProfile(
            name="RJ Startup",
            slug="rj-startup",
            description="Healthtech app",
            sector="HealthTech",
            city="Rio de Janeiro",
            country="Brasil",
            source_url="https://github.com/rj-startup",
            source_name="github_rio",
        ),
        CompanyProfile(
            name="MX Company",
            slug="mx-company",
            description="Edtech platform",
            sector="Edtech",
            city="Mexico City",
            country="Mexico",
            source_url="https://github.com/mx-company",
            source_name="github_mexico_city",
        ),
    ]

    result = mercado_agent.run()

    # Verify multi-city report
    assert "São Paulo" in result.body_md
    assert "Rio de Janeiro" in result.body_md
    assert "Mexico City" in result.body_md
    assert "Fintech" in result.body_md
    assert "HealthTech" in result.body_md
    assert "Edtech" in result.body_md
