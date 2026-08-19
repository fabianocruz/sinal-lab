"""End-to-end tests for MERCADO v2 agent.

MERCADO v2 is a READER: it queries funding_rounds/companies (populated
by FUNDING and INDEX) and produces a weekly editorial analysis. These
tests mock the database collectors and force the LLM writer offline so
every phase runs its deterministic fallback path.
"""

from datetime import date
from unittest.mock import PropertyMock, patch

import pytest

from apps.agents.mercado.agent import MercadoAgent
from apps.agents.mercado.market_event import MarketEvent, ScoredEvent
from apps.agents.mercado.v2_writer import MercadoV2Writer


def _make_event(
    name: str,
    slug: str,
    sector: str = "Fintech",
    amount: float = 10_000_000.0,
    **overrides,
) -> MarketEvent:
    fields = dict(
        company_name=name,
        company_slug=slug,
        event_type="funding_round",
        occurred_at=date(2026, 2, 10),
        sector=sector,
        country="Brasil",
        city="São Paulo",
        amount_usd=amount,
        round_type="Series A",
        source_url=f"https://news.example.dev/{slug}",
        source_name="latamlist",
    )
    fields.update(overrides)
    return MarketEvent(**fields)


@pytest.fixture
def offline_writer():
    """Force the LLM writer offline so outputs use deterministic fallbacks."""
    with patch.object(
        MercadoV2Writer, "is_available", new_callable=PropertyMock, return_value=False
    ):
        yield


@pytest.fixture
def mercado_agent():
    """Create MercadoAgent instance for testing."""
    return MercadoAgent(week_number=7)


def test_agent_initialization(mercado_agent):
    """Test agent initialization."""
    assert mercado_agent.agent_name == "mercado"
    assert mercado_agent.week_number == 7
    assert mercado_agent.run_id.startswith("mercado-")


@patch("apps.agents.mercado.agent.enrich_events_with_companies")
@patch("apps.agents.mercado.agent.collect_funding_events")
@patch("packages.database.session.get_session")
def test_collect_phase(mock_get_session, mock_collect, mock_enrich, mercado_agent):
    """Collect reads funding events from the DB via the v2 collector."""
    events = [_make_event(f"Empresa {i}", f"empresa-{i}") for i in range(5)]
    mock_collect.return_value = events
    mock_enrich.side_effect = lambda session, evs: evs

    result = mercado_agent.collect()

    assert len(result) == 5
    assert isinstance(result[0], MarketEvent)
    mock_collect.assert_called_once_with(
        mock_get_session.return_value, days_back=7
    )


@patch("apps.agents.mercado.agent.enrich_events_with_companies")
@patch("apps.agents.mercado.agent.collect_funding_events")
@patch("packages.database.session.get_session")
def test_collect_widens_window_on_thin_week(
    mock_get_session, mock_collect, mock_enrich, mercado_agent
):
    """Fewer than 5 events in 7 days re-collects with a 14-day window."""
    thin_week = [_make_event("Solo", "solo")]
    wide_week = [_make_event("Solo", "solo"), _make_event("Outra", "outra")]
    mock_collect.side_effect = [thin_week, wide_week]
    mock_enrich.side_effect = lambda session, evs: evs

    result = mercado_agent.collect()

    assert len(result) == 2
    assert mock_collect.call_count == 2
    assert mock_collect.call_args_list[1].kwargs["days_back"] == 14


def test_process_phase_groups_events_into_sections(mercado_agent):
    """Process groups events by editorial sector bucket."""
    events = [
        _make_event("PagueBem", "paguebem", sector="Fintech"),
        _make_event("CreditoJa", "creditoja", sector="Fintech"),
    ]

    sections = mercado_agent.process(events)

    assert len(sections) == 1
    assert sections[0].sector_slug == "fintech"
    assert len(sections[0].events) == 2


def test_process_phase_drops_sectors_below_minimum(mercado_agent):
    """Buckets with fewer than 2 events are dropped from the edition."""
    sections = mercado_agent.process([_make_event("Sozinha", "sozinha")])

    assert sections == []


def test_score_phase(mercado_agent):
    """Score ranks events per section and aggregates confidence."""
    sections = mercado_agent.process([
        _make_event("PagueBem", "paguebem"),
        _make_event("CreditoJa", "creditoja"),
    ])

    scores = mercado_agent.score(sections)

    assert len(scores) == 1
    assert 0.0 <= scores[0].data_quality <= 1.0
    assert 0.0 <= scores[0].analysis_confidence <= 1.0
    assert scores[0].source_count >= 1
    # Sections now hold ScoredEvents with editorial relevance
    for section in mercado_agent._sections:
        for scored in section.events:
            assert isinstance(scored, ScoredEvent)
            assert 0.0 <= scored.editorial_score <= 1.0


def test_score_phase_with_no_sections(mercado_agent):
    """Empty week still yields a (low) confidence score."""
    scores = mercado_agent.score([])

    assert len(scores) == 1
    assert scores[0].data_quality == 0.3
    assert scores[0].analysis_confidence == 0.3


def test_output_phase(offline_writer, mercado_agent):
    """Output produces newsletter Markdown + metadata from sections."""
    sections = mercado_agent.process([
        _make_event("BigCorp", "bigcorp", amount=50_000_000.0),
        _make_event("OtherCo", "otherco", amount=8_000_000.0),
    ])
    scores = mercado_agent.score(sections)

    output = mercado_agent.output(sections, scores)

    assert output.agent_name == "mercado"
    assert output.content_type == "NEWSLETTER"
    assert "BigCorp" in output.body_md
    assert "OtherCo" in output.body_md
    # Offline writer → deterministic fallback title
    assert output.title.startswith("Market Intelligence LATAM")
    assert output.metadata["item_count"] == 2
    assert output.metadata["week_number"] == 7
    assert len(output.sources) == 2


@patch("apps.agents.mercado.agent.enrich_events_with_companies")
@patch("apps.agents.mercado.agent.collect_funding_events")
@patch("packages.database.session.get_session")
def test_full_agent_run(
    mock_get_session, mock_collect, mock_enrich, offline_writer, mercado_agent
):
    """Complete run end-to-end: collect -> process -> score -> output."""
    mock_collect.return_value = [
        _make_event(f"Fintech {i}", f"fintech-{i}") for i in range(5)
    ]
    mock_enrich.side_effect = lambda session, evs: evs

    result = mercado_agent.run()

    assert result is not None
    assert "Fintech 0" in result.body_md
    assert result.confidence.composite > 0
    assert result.metadata["item_count"] == 5


@patch("apps.agents.mercado.agent.enrich_events_with_companies")
@patch("apps.agents.mercado.agent.collect_funding_events")
@patch("packages.database.session.get_session")
def test_agent_run_with_no_events(
    mock_get_session, mock_collect, mock_enrich, offline_writer, mercado_agent
):
    """Empty funding week produces the explicit low-volume report."""
    mock_collect.return_value = []
    mock_enrich.side_effect = lambda session, evs: evs

    result = mercado_agent.run()

    assert result is not None
    assert "Semana sem volume suficiente" in result.body_md
    # Both the 7d and the widened 14d window were tried
    assert mock_collect.call_count == 2


@patch("apps.agents.mercado.agent.enrich_events_with_companies")
@patch("apps.agents.mercado.agent.collect_funding_events")
@patch("packages.database.session.get_session")
def test_agent_run_multiple_sectors(
    mock_get_session, mock_collect, mock_enrich, offline_writer, mercado_agent
):
    """Events across sectors and countries all land in the report."""
    mock_collect.return_value = [
        _make_event("SP Fintech", "sp-fintech", sector="Fintech"),
        _make_event("MX Fintech", "mx-fintech", sector="Fintech",
                    city="Mexico City", country="Mexico"),
        _make_event("RJ Health", "rj-health", sector="HealthTech",
                    city="Rio de Janeiro"),
        _make_event("BA Health", "ba-health", sector="HealthTech",
                    city="Buenos Aires", country="Argentina"),
        _make_event("SP Edtech", "sp-edtech", sector="Edtech"),
    ]
    mock_enrich.side_effect = lambda session, evs: evs

    result = mercado_agent.run()

    for company in ["SP Fintech", "MX Fintech", "RJ Health", "BA Health", "SP Edtech"]:
        assert company in result.body_md
    for city in ["São Paulo", "Mexico City", "Rio de Janeiro", "Buenos Aires"]:
        assert city in result.body_md
