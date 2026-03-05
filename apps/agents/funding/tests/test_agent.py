"""End-to-end tests for FUNDING agent."""

import pytest
from unittest.mock import patch, Mock

from apps.agents.funding.agent import FundingAgent
from apps.agents.funding.collector import FundingEvent
from datetime import date


@pytest.fixture
def funding_agent():
    """Create FundingAgent instance for testing."""
    return FundingAgent(week_number=7)


def test_agent_initialization(funding_agent):
    """Test agent initialization."""
    assert funding_agent.agent_name == "funding"
    assert funding_agent.week_number == 7
    assert funding_agent.run_id.startswith("funding-")


@patch('apps.agents.funding.agent.collect_all_sources')
def test_collect_phase(mock_collect, funding_agent):
    """Test collect phase returns FundingEvent list."""
    # Mock collector to return sample events
    sample_events = [
        FundingEvent(
            company_name="Startup A",
            round_type="series_a",
            source_url="https://test.com/1",
            source_name="test",
            amount_usd=10.0,
            announced_date=date.today(),
        ),
        FundingEvent(
            company_name="Startup B",
            round_type="seed",
            source_url="https://test.com/2",
            source_name="test",
            amount_usd=2.0,
            announced_date=date.today(),
        ),
    ]
    mock_collect.return_value = sample_events

    result = funding_agent.collect()

    assert len(result) == 2
    assert isinstance(result[0], FundingEvent)
    assert mock_collect.called


def test_process_phase(funding_agent):
    """Test process phase normalizes and deduplicates."""
    raw_events = [
        FundingEvent(
            company_name="Test Co",
            round_type="Series A Round",  # Will be normalized
            source_url="https://test.com/1",
            source_name="test",
            amount_local=50.0,
            currency="BRL",  # Will be converted to USD
            announced_date=date.today(),
        ),
    ]

    processed = funding_agent.process(raw_events)

    assert len(processed) > 0
    # Check normalization happened
    assert processed[0].round_type == "series_a"
    assert processed[0].amount_usd is not None  # BRL converted to USD


def test_score_phase(funding_agent):
    """Test score phase returns ConfidenceScore list."""
    events = [
        FundingEvent(
            company_name="Test Co",
            round_type="series_a",
            source_url="https://test.com",
            source_name="test",
            amount_usd=10.0,
            announced_date=date.today(),
        ),
    ]

    scores = funding_agent.score(events)

    assert len(scores) > 0
    assert hasattr(scores[0], 'data_quality')
    assert hasattr(scores[0], 'analysis_confidence')


def test_output_phase(funding_agent):
    """Test output phase generates AgentOutput."""
    events = [
        FundingEvent(
            company_name="Big Corp",
            round_type="series_a",
            source_url="https://test.com",
            source_name="test",
            amount_usd=50.0,
            announced_date=date.today(),
            company_slug="big-corp",
        ),
    ]

    scores = funding_agent.score(events)
    output = funding_agent.output(events, scores)

    assert len(output.title) > 10  # LLM-generated or fallback title
    assert len(output.body_md) > 0
    assert output.agent_name == "funding"
    assert output.content_type == "DATA_REPORT"


@patch('apps.agents.funding.agent.collect_all_sources')
def test_full_agent_run(mock_collect, funding_agent):
    """Test complete agent run end-to-end."""
    # Mock collector
    mock_collect.return_value = [
        FundingEvent(
            company_name="Test Startup",
            round_type="series_a",
            source_url="https://test.com",
            source_name="test",
            amount_usd=15.0,
            announced_date=date.today(),
            company_slug="test-startup",
            lead_investors=["VC Fund"],
        ),
    ]

    # Run agent
    result = funding_agent.run()

    # Verify output
    assert result is not None
    assert len(result.title) > 10  # LLM-generated or fallback title
    assert "Test Startup" in result.body_md
    # Note: sources won't be tracked when using mocked collector
    assert result.confidence.composite > 0


def test_agent_run_with_no_events(funding_agent):
    """Test agent run with empty event list."""
    with patch('apps.agents.funding.collector.collect_all_sources', return_value=[]):
        result = funding_agent.run()

        # Should still produce output (empty report)
        assert result is not None
        assert len(result.body_md) > 0


# --- SEC Integration Agent Tests ---


@patch('apps.agents.funding.agent.collect_all_sources')
def test_score_calls_cross_ref_verification(mock_collect, funding_agent):
    """Score method calls apply_cross_ref_verification."""
    events = [
        FundingEvent(
            company_name="TestCo",
            round_type="series_a",
            source_url="https://test.com",
            source_name="test",
            amount_usd=10.0,
            announced_date=date.today(),
        ),
        FundingEvent(
            company_name="TestCo",
            round_type="unknown",
            source_url="https://sec.gov/testco",
            source_name="sec_form_d",
            amount_usd=10.0,
            announced_date=date.today(),
        ),
    ]

    scores = funding_agent.score(events)

    # Should have scores for both events
    assert len(scores) == 2
    # SEC event should have regulatory floor
    sec_scores = [s for s in scores if s.data_quality >= 0.85]
    assert len(sec_scores) >= 1


@patch('apps.agents.funding.agent.collect_all_sources')
def test_agent_run_without_sec_source(mock_collect, funding_agent):
    """Agent runs fine without SEC source (backward compatible)."""
    mock_collect.return_value = [
        FundingEvent(
            company_name="Normal Co",
            round_type="seed",
            source_url="https://test.com/normal",
            source_name="startupi",
            amount_usd=5.0,
            announced_date=date.today(),
        ),
    ]

    result = funding_agent.run()

    assert result is not None
    assert "Normal Co" in result.body_md


@patch('apps.agents.funding.agent.collect_all_sources')
def test_agent_run_with_sec_source(mock_collect, funding_agent):
    """Agent integrates SEC events in the run output."""
    mock_collect.return_value = [
        FundingEvent(
            company_name="Big Corp",
            round_type="series_b",
            source_url="https://test.com/bigcorp",
            source_name="crunchbase_news",
            amount_usd=50.0,
            announced_date=date.today(),
            company_slug="big-corp",
        ),
        FundingEvent(
            company_name="Big Corp LLC",
            round_type="unknown",
            source_url="https://sec.gov/bigcorp",
            source_name="sec_form_d",
            amount_usd=50.0,
            announced_date=date.today(),
        ),
    ]

    result = funding_agent.run()

    assert result is not None
    assert result.confidence.composite > 0
