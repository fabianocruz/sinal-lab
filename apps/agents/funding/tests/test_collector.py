"""Tests for FUNDING agent collector."""

import pytest
from datetime import date

from apps.agents.funding.collector import (
    FundingEvent,
    clean_rss_notes,
    extract_funding_from_title,
    parse_funding_event,
)


def test_funding_event_creation():
    """Test FundingEvent dataclass creation."""
    event = FundingEvent(
        company_name="Test Startup",
        round_type="series_a",
        source_url="https://example.com",
        source_name="test_source",
        amount_usd=10.0,
    )

    assert event.company_name == "Test Startup"
    assert event.round_type == "series_a"
    assert event.amount_usd == 10.0
    assert event.content_hash  # Should be auto-generated


def test_extract_funding_from_title_series_a():
    """Test extracting funding info from title with Series A."""
    title = "Nubank raises $500M Series A"
    info = extract_funding_from_title(title)

    assert info is not None
    assert "Nubank" in info["company_name"]
    assert info["amount"] == 500.0
    assert info["currency"] == "USD"
    assert "series_a" in info["round_type"]


def test_extract_funding_from_title_portuguese():
    """Test extracting funding from Portuguese title."""
    title = "Stone recebe aporte de R$ 50 milhões em rodada Série B"
    info = extract_funding_from_title(title)

    assert info is not None
    assert "Stone" in info["company_name"]
    assert info["amount"] == 50.0
    assert info["currency"] == "BRL"


def test_extract_funding_from_title_no_match():
    """Test title with no funding info."""
    title = "Company announces new product launch"
    info = extract_funding_from_title(title)

    assert info is None


class MockEntry:
    """Mock feedparser entry for testing."""

    def __init__(self, title, link, summary=""):
        self.title = title
        self.link = link
        self.summary = summary


def test_parse_funding_event_valid():
    """Test parsing a valid feed entry."""
    entry = MockEntry(
        title="Creditas levanta US$ 15M em rodada Série A",
        link="https://example.com/article",
        summary="Startup brasileira recebe investimento liderado por Kaszek",
    )

    event = parse_funding_event(entry, "test_source")

    assert event is not None
    assert "Creditas" in event.company_name
    assert event.amount_usd == 15.0
    assert event.round_type == "series_a"
    assert event.source_name == "test_source"


def test_parse_funding_event_invalid():
    """Test parsing entry without funding info."""
    entry = MockEntry(
        title="Tech company releases quarterly earnings",
        link="https://example.com/earnings",
    )

    event = parse_funding_event(entry, "test_source")

    assert event is None


class TestFundingEventDedup:
    """Test that FundingEvent deduplicates by company+round, not source URL."""

    def test_same_company_different_sources_same_hash(self):
        """Same company + round from different sources should have same hash."""
        event1 = FundingEvent(
            company_name="Avenia",
            round_type="series_a",
            source_url="https://startupi.com.br/avenia",
            source_name="startupi",
        )
        event2 = FundingEvent(
            company_name="Avenia",
            round_type="series_a",
            source_url="https://latamlist.com/avenia",
            source_name="latamlist",
        )
        assert event1.content_hash == event2.content_hash

    def test_hash_case_insensitive(self):
        """Hash should be case-insensitive on company name."""
        event1 = FundingEvent(
            company_name="Avenia",
            round_type="series_a",
            source_url="https://example.com/1",
            source_name="source1",
        )
        event2 = FundingEvent(
            company_name="avenia",
            round_type="series_a",
            source_url="https://example.com/2",
            source_name="source2",
        )
        assert event1.content_hash == event2.content_hash

    def test_different_round_types_different_hash(self):
        """Different round types should produce different hashes."""
        event1 = FundingEvent(
            company_name="Avenia",
            round_type="series_a",
            source_url="https://example.com",
            source_name="source",
        )
        event2 = FundingEvent(
            company_name="Avenia",
            round_type="seed",
            source_url="https://example.com",
            source_name="source",
        )
        assert event1.content_hash != event2.content_hash

    def test_different_companies_different_hash(self):
        """Different companies should produce different hashes."""
        event1 = FundingEvent(
            company_name="Avenia",
            round_type="series_a",
            source_url="https://example.com",
            source_name="source",
        )
        event2 = FundingEvent(
            company_name="BemAgro",
            round_type="series_a",
            source_url="https://example.com",
            source_name="source",
        )
        assert event1.content_hash != event2.content_hash


class TestCleanRssNotes:
    """Test RSS boilerplate cleaning."""

    def test_strips_english_boilerplate(self):
        text = "Brazilian fintech raised $17M. The post Avenia raises $17M Series A appeared first on LatamList."
        result = clean_rss_notes(text)
        assert result == "Brazilian fintech raised $17M."

    def test_strips_portuguese_boilerplate(self):
        text = "Startup brasileira levantou $17M. O post Avenia levanta $17M apareceu primeiro em Startupi."
        result = clean_rss_notes(text)
        assert result == "Startup brasileira levantou $17M."

    def test_no_boilerplate_unchanged(self):
        text = "Normal notes without boilerplate."
        result = clean_rss_notes(text)
        assert result == "Normal notes without boilerplate."

    def test_empty_string(self):
        assert clean_rss_notes("") == ""

    def test_only_boilerplate(self):
        text = "The post Something appeared first on LatamList."
        result = clean_rss_notes(text)
        assert result == ""


# --- SEC Form D Integration Tests ---

from unittest.mock import patch, MagicMock
from apps.agents.base.config import DataSourceConfig
from apps.agents.base.provenance import ProvenanceTracker


@patch("apps.agents.sources.sec_form_d.fetch_sec_form_d")
def test_sec_form_d_events_collected(mock_fetch_sec):
    """SEC Form D filings are converted to FundingEvents when SEC source is present."""
    from apps.agents.sources.sec_form_d import SECFormDFiling
    from apps.agents.funding.collector import collect_all_sources

    mock_fetch_sec.return_value = [
        SECFormDFiling(
            company_name="Nubank Capital LLC",
            cik="0001234567",
            source_url="https://www.sec.gov/cgi-bin/browse-edgar?CIK=0001234567",
            date_filed=date(2026, 2, 15),
            amount_sold=750_000_000.0,
        ),
    ]

    sources = [
        DataSourceConfig(
            name="test_rss",
            source_type="rss",
            url="https://example.com/feed",
            enabled=False,  # Disabled to avoid real HTTP calls
        ),
        DataSourceConfig(
            name="sec_form_d",
            source_type="api",
            url="https://efts.sec.gov/LATEST/search-index",
        ),
    ]
    provenance = ProvenanceTracker()

    # Need at least one initial event for SEC to trigger
    with patch("apps.agents.funding.collector.fetch_feed") as mock_feed:
        mock_feed.return_value = [
            FundingEvent(
                company_name="Nubank",
                round_type="series_g",
                source_url="https://example.com/nubank",
                source_name="test_rss",
                amount_usd=750.0,
            ),
        ]
        # Re-enable RSS source for this path
        sources[0].enabled = True
        events = collect_all_sources(sources, provenance, "funding", "test-run")

    # Should have RSS event + SEC event
    assert any(e.source_name == "sec_form_d" for e in events)
    sec_event = [e for e in events if e.source_name == "sec_form_d"][0]
    assert sec_event.round_type == "unknown"
    assert "SEC CIK" in sec_event.notes


@patch("apps.agents.funding.collector._load_from_funding_rounds_table", return_value=[])
def test_sec_skipped_when_no_sec_source(mock_load_db):
    """No SEC calls when sec_form_d source is not configured."""
    from apps.agents.funding.collector import collect_all_sources

    sources = [
        DataSourceConfig(
            name="test_rss",
            source_type="rss",
            url="https://example.com/feed",
            enabled=False,
        ),
    ]
    provenance = ProvenanceTracker()

    # Should not raise, just return empty (no enabled sources)
    events = collect_all_sources(sources, provenance, "funding", "test-run")
    assert events == []


@patch("apps.agents.funding.collector._load_from_funding_rounds_table", return_value=[])
def test_sec_skipped_when_no_initial_events(mock_load_db):
    """SEC collection skipped when initial RSS/API collection returns nothing."""
    from apps.agents.funding.collector import collect_all_sources

    sources = [
        DataSourceConfig(
            name="sec_form_d",
            source_type="api",
            url="https://efts.sec.gov/LATEST/search-index",
        ),
    ]
    provenance = ProvenanceTracker()

    # No initial events → sec_sources check passes but all_events is empty
    events = collect_all_sources(sources, provenance, "funding", "test-run")
    assert events == []


@patch("apps.agents.funding.collector._load_from_funding_rounds_table", return_value=[])
@patch("apps.agents.sources.sec_form_d.fetch_sec_form_d")
def test_sec_graceful_degradation(mock_fetch_sec, mock_load_db):
    """SEC API failure doesn't break other event collection."""
    from apps.agents.funding.collector import collect_all_sources

    mock_fetch_sec.side_effect = Exception("SEC API down")

    sources = [
        DataSourceConfig(
            name="sec_form_d",
            source_type="api",
            url="https://efts.sec.gov/LATEST/search-index",
        ),
    ]
    provenance = ProvenanceTracker()

    # Pre-populate with a mock RSS event via patching
    with patch("apps.agents.funding.collector.fetch_feed") as mock_feed:
        mock_feed.return_value = [
            FundingEvent(
                company_name="TestCo",
                round_type="seed",
                source_url="https://example.com/testco",
                source_name="test_rss",
            ),
        ]
        rss_source = DataSourceConfig(name="test_rss", source_type="rss", url="https://example.com/feed")
        events = collect_all_sources([rss_source] + sources, provenance, "funding", "test-run")

    # RSS events should still be returned despite SEC failure
    assert len(events) >= 1
    assert events[0].source_name == "test_rss"


@patch("apps.agents.sources.sec_form_d.fetch_sec_form_d")
def test_company_names_limited_to_20(mock_fetch_sec):
    """Only top 20 unique company names are sent to SEC."""
    from apps.agents.funding.collector import collect_all_sources
    from apps.agents.sources.sec_form_d import SECFormDFiling

    mock_fetch_sec.return_value = []

    # Create 25 unique events
    rss_events = [
        FundingEvent(
            company_name=f"Company_{i}",
            round_type="seed",
            source_url=f"https://example.com/{i}",
            source_name="test_rss",
        )
        for i in range(25)
    ]

    sources = [
        DataSourceConfig(name="sec_form_d", source_type="api", url="https://efts.sec.gov/LATEST/search-index"),
    ]
    provenance = ProvenanceTracker()

    with patch("apps.agents.funding.collector.fetch_feed") as mock_feed:
        rss_source = DataSourceConfig(name="test_rss", source_type="rss", url="https://example.com/feed")
        mock_feed.return_value = rss_events
        collect_all_sources([rss_source] + sources, provenance, "funding", "test-run")

    # Verify SEC was called with at most 20 company names
    assert mock_fetch_sec.called
    company_names_arg = mock_fetch_sec.call_args[0][2]  # 3rd positional arg
    assert len(company_names_arg) <= 20


# ---------------------------------------------------------------------------
# LLM fallback extraction (regex miss -> keyword prefilter -> LLM)
# ---------------------------------------------------------------------------

import json

from apps.agents.base.llm import LLMClient
from apps.agents.funding.collector import (
    EXTRACTION_METHOD_LLM,
    EXTRACTION_METHOD_REGEX,
    LLMFundingExtractor,
    looks_like_funding_news,
)


def _mock_llm(response=None, side_effect=None, available=True):
    """Build a mock LLMClient with a canned generate() response."""
    client = MagicMock(spec=LLMClient)
    client.is_available = available
    if side_effect is not None:
        client.generate.side_effect = side_effect
    else:
        client.generate.return_value = response
    return client


def _llm_payload(**overrides):
    """Build a valid LLM extraction JSON payload."""
    payload = {
        "is_funding_event": True,
        "company_name": "Zenpli",
        "amount": 6_500_000,
        "currency": "USD",
        "round_type": "seed",
        "investors": ["Maya Capital", "Race Capital"],
    }
    payload.update(overrides)
    return json.dumps(payload)


class TestLooksLikeFundingNews:
    """Keyword pre-filter that gates (expensive) LLM extraction."""

    @pytest.mark.parametrize("title", [
        "Zenpli raises $6.5M to expand across LATAM",
        "Fintech brasileira capta R$ 30 milhões em rodada seed",
        "Startup mexicana cierra ronda de inversión de US$ 12 millones",
        "Kaszek lidera aporte na Creditas",
        "CloudWalk announces Series C funding",
    ])
    def test_funding_titles_pass(self, title):
        assert looks_like_funding_news(title) is True

    @pytest.mark.parametrize("title", [
        "Apple lança novo iPhone com chip proprietário",
        "How we scaled Postgres to 10 million rows",
        "Conheça os 10 melhores frameworks de 2026",
    ])
    def test_unrelated_titles_rejected(self, title):
        assert looks_like_funding_news(title) is False

    def test_body_is_considered(self):
        """Signal may live only in the body, not the title."""
        assert looks_like_funding_news(
            "Novidades da semana",
            "A empresa levantou US$ 4 milhões em rodada seed liderada por Canary.",
        ) is True

    def test_empty_inputs(self):
        assert looks_like_funding_news("", "") is False


class TestParseFundingEventLLMFallback:
    """parse_funding_event: regex first, LLM fallback second."""

    def test_regex_match_skips_llm(self):
        """(a) Regex path still works and never spends an LLM call."""
        client = _mock_llm(response=_llm_payload())
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Creditas levanta US$ 15M em rodada Série A",
            link="https://example.com/creditas",
            summary="Rodada liderada por Kaszek",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is not None
        assert event.amount_usd == 15.0
        assert event.round_type == "series_a"
        assert event.extraction_method == EXTRACTION_METHOD_REGEX
        client.generate.assert_not_called()

    def test_prefilter_rejects_without_llm_call(self):
        """(b) Regex miss + irrelevant item -> None, no LLM call (cost control)."""
        client = _mock_llm(response=_llm_payload())
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Como usamos Rust para reduzir latência em 40%",
            link="https://example.com/rust",
            summary="Um estudo de caso de engenharia de plataforma.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is None
        client.generate.assert_not_called()

    def test_llm_extracts_event_regex_missed(self):
        """(c) Regex miss + prefilter pass + valid LLM output -> structured event."""
        client = _mock_llm(response=_llm_payload())
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Zenpli, de identidade digital, anuncia captação para crescer no México",
            link="https://example.com/zenpli",
            summary="A startup fechou uma rodada seed de US$ 6,5 milhões.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is not None
        assert event.company_name == "Zenpli"
        assert event.amount_usd == 6_500_000
        assert event.round_type == "seed"
        assert event.lead_investors == ["Maya Capital", "Race Capital"]
        assert event.extraction_method == EXTRACTION_METHOD_LLM
        assert event.source_url == "https://example.com/zenpli"
        client.generate.assert_called_once()

    def test_llm_rejects_false_positive(self):
        """(d) LLM says it is not a funding event -> None."""
        client = _mock_llm(response=_llm_payload(is_funding_event=False))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Fundo levanta debate sobre valuation de startups",
            link="https://example.com/opinion",
            summary="Análise sobre rodadas e múltiplos no mercado LATAM.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is None
        client.generate.assert_called_once()

    def test_llm_error_does_not_crash(self):
        """(e) LLM raising must degrade to None, not break collection."""
        client = _mock_llm(side_effect=RuntimeError("api exploded"))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Startup argentina capta investimento para expansão regional",
            link="https://example.com/arg",
            summary="A rodada foi liderada por um fundo local.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is None

    def test_llm_invalid_json_returns_none(self):
        client = _mock_llm(response="desculpe, não consegui extrair nada")
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Startup chilena capta rodada para expandir",
            link="https://example.com/cl",
            summary="Detalhes não foram divulgados.",
        )

        assert parse_funding_event(entry, "test_source", extractor=extractor) is None

    def test_llm_output_in_code_fences_is_parsed(self):
        client = _mock_llm(response="```json\n" + _llm_payload() + "\n```")
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Zenpli anuncia captação seed",
            link="https://example.com/zenpli",
            summary="Rodada seed de US$ 6,5 milhões.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is not None
        assert event.company_name == "Zenpli"

    def test_llm_incomplete_payload_returns_none(self):
        """Company only (no amount, unknown round) is not useful -> None."""
        client = _mock_llm(response=_llm_payload(
            amount=None, round_type="unknown", investors=[],
        ))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Startup peruana capta rodada de valor não revelado",
            link="https://example.com/pe",
            summary="O aporte não teve valor divulgado.",
        )

        assert parse_funding_event(entry, "test_source", extractor=extractor) is None

    def test_llm_missing_company_returns_none(self):
        client = _mock_llm(response=_llm_payload(company_name=""))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Rodada seed movimenta o ecossistema, capta atenção de fundos",
            link="https://example.com/x",
            summary="Investimento de US$ 3 milhões.",
        )

        assert parse_funding_event(entry, "test_source", extractor=extractor) is None

    def test_round_type_only_is_enough(self):
        """company + round_type (no amount) is still a usable signal."""
        client = _mock_llm(response=_llm_payload(amount=None, round_type="Series B"))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Zenpli fecha rodada Série B sem revelar valores",
            link="https://example.com/zenpli-b",
            summary="A captação contou com investidores existentes.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is not None
        assert event.round_type == "series_b"
        assert event.amount_usd is None

    def test_local_currency_goes_to_amount_local(self):
        client = _mock_llm(response=_llm_payload(amount=30_000_000, currency="BRL"))
        extractor = LLMFundingExtractor(client=client)
        entry = MockEntry(
            title="Fintech carioca capta R$ 30 milhões em rodada",
            link="https://example.com/brl",
            summary="Aporte liderado por fundo local.",
        )

        event = parse_funding_event(entry, "test_source", extractor=extractor)

        assert event is not None
        assert event.currency == "BRL"
        assert event.amount_local == 30_000_000
        assert event.amount_usd is None

    def test_no_extractor_keeps_legacy_behaviour(self):
        """Without an extractor, a regex miss is dropped exactly as before."""
        entry = MockEntry(
            title="Startup capta rodada seed de US$ 2 milhões",
            link="https://example.com/legacy",
            summary="Rodada liderada por fundo local.",
        )

        assert parse_funding_event(entry, "test_source") is None


class TestLLMFundingExtractorBudget:
    """The extractor caps LLM spend per run."""

    def test_budget_limits_calls(self):
        client = _mock_llm(response=_llm_payload())
        extractor = LLMFundingExtractor(client=client, max_calls=1)

        first = extractor.extract("Startup capta rodada seed", "US$ 6,5 milhões")
        second = extractor.extract("Outra startup capta rodada seed", "US$ 2 milhões")

        assert first is not None
        assert second is None
        assert client.generate.call_count == 1

    def test_unavailable_client_never_called(self):
        client = _mock_llm(response=_llm_payload(), available=False)
        extractor = LLMFundingExtractor(client=client)

        assert extractor.extract("Startup capta rodada seed", "US$ 6,5 milhões") is None
        assert extractor.is_available is False
        client.generate.assert_not_called()

    def test_calls_used_is_tracked(self):
        client = _mock_llm(response=_llm_payload())
        extractor = LLMFundingExtractor(client=client, max_calls=5)

        extractor.extract("Startup capta rodada seed", "US$ 6,5 milhões")

        assert extractor.calls_used == 1


# ---------------------------------------------------------------------------
# HTML sources (VC blogs that serve rendered HTML instead of RSS)
# ---------------------------------------------------------------------------

from datetime import datetime, timezone


@patch("apps.agents.funding.collector._load_from_funding_rounds_table", return_value=[])
@patch("apps.agents.sources.web_scraper.scrape_article_listing")
class TestHtmlSourceCollection:
    """collect_all_sources dispatches source_type='html' to the scraper."""

    def _html_source(self):
        return DataSourceConfig(
            name="maya_capital",
            source_type="html",
            url="https://maya.capital/blog",
            params={"max_items": 5, "fetch_content": True},
        )

    def test_html_source_produces_events(self, mock_scrape, mock_db):
        from apps.agents.funding.collector import collect_all_sources

        mock_scrape.return_value = [
            {
                "title": "Sharpi levanta US$ 4M em rodada Série A",
                "url": "https://maya.capital/blog/sharpi.html",
                "published_at": datetime(2026, 8, 10, tzinfo=timezone.utc),
                "summary": "Rodada liderada por Maya Capital",
                "source_name": "maya_capital",
                "content_hash": "abc",
            },
        ]
        provenance = ProvenanceTracker()

        events = collect_all_sources(
            [self._html_source()], provenance, "funding", "test-run"
        )

        assert len(events) == 1
        assert events[0].company_name == "Sharpi"
        assert events[0].source_name == "maya_capital"
        assert events[0].announced_date == date(2026, 8, 10)
        assert events[0].extraction_method == EXTRACTION_METHOD_REGEX
        assert mock_scrape.call_count == 1
        assert provenance.records[0].extraction_method == "scraper"

    def test_html_items_without_funding_are_dropped(self, mock_scrape, mock_db):
        from apps.agents.funding.collector import collect_all_sources

        mock_scrape.return_value = [
            {
                "title": "Nosso time cresceu: conheça os novos sócios",
                "url": "https://maya.capital/blog/time.html",
                "published_at": None,
                "summary": "Novidades internas do fundo.",
                "source_name": "maya_capital",
                "content_hash": "def",
            },
        ]

        events = collect_all_sources(
            [self._html_source()], ProvenanceTracker(), "funding", "test-run"
        )

        assert events == []

    def test_html_scrape_failure_is_isolated(self, mock_scrape, mock_db):
        """A broken blog must not abort the whole collection run."""
        from apps.agents.funding.collector import collect_all_sources

        mock_scrape.side_effect = RuntimeError("site down")

        events = collect_all_sources(
            [self._html_source()], ProvenanceTracker(), "funding", "test-run"
        )

        assert events == []

    def test_rss_sources_still_use_fetch_feed(self, mock_scrape, mock_db):
        """Regression: RSS sources are untouched by the HTML branch."""
        from apps.agents.funding.collector import collect_all_sources

        rss_source = DataSourceConfig(
            name="latamlist", source_type="rss", url="https://latamlist.com/feed/"
        )

        with patch("apps.agents.funding.collector.fetch_feed") as mock_feed:
            mock_feed.return_value = [
                FundingEvent(
                    company_name="Avenia",
                    round_type="series_a",
                    source_url="https://latamlist.com/avenia",
                    source_name="latamlist",
                ),
            ]
            events = collect_all_sources(
                [rss_source], ProvenanceTracker(), "funding", "test-run"
            )

        assert [e.company_name for e in events] == ["Avenia"]
        mock_scrape.assert_not_called()
        mock_feed.assert_called_once()


# ---------------------------------------------------------------------------
# Grok Live Search source
# ---------------------------------------------------------------------------


@patch("apps.agents.funding.collector._load_from_funding_rounds_table", return_value=[])
@patch("apps.agents.sources.grok_search.fetch_grok_funding_rounds")
class TestGrokSourceCollection:
    """collect_all_sources dispatches the grok_live_search API source."""

    def _grok_source(self):
        return DataSourceConfig(
            name="grok_live_search",
            source_type="api",
            url="https://api.x.ai/v1/responses",
            api_key_env="XAI_API_KEY",
            params={"model": "grok-4.3", "days_back": 7},
        )

    def test_grok_events_become_funding_events(self, mock_fetch, mock_db):
        from apps.agents.funding.collector import EXTRACTION_METHOD_GROK, collect_all_sources
        from apps.agents.sources.grok_search import GrokFundingEvent

        mock_fetch.return_value = [
            GrokFundingEvent(
                company_name="Kesh",
                source_name="grok_live_search",
                amount=110_000_000.0,
                currency="USD",
                round_type="series_b",
                investors=["Grupo Leste"],
                source_url="https://example.com/kesh",
                announced_date=date(2026, 8, 6),
                country="BR",
            ),
        ]
        provenance = ProvenanceTracker()

        events = collect_all_sources(
            [self._grok_source()], provenance, "funding", "test-run"
        )

        assert len(events) == 1
        event = events[0]
        assert event.company_name == "Kesh"
        assert event.amount_usd == 110_000_000.0
        assert event.round_type == "series_b"
        assert event.lead_investors == ["Grupo Leste"]
        assert event.announced_date == date(2026, 8, 6)
        assert event.extraction_method == EXTRACTION_METHOD_GROK
        assert provenance.records[0].extraction_method == "api"

    def test_local_currency_goes_to_amount_local(self, mock_fetch, mock_db):
        from apps.agents.funding.collector import collect_all_sources
        from apps.agents.sources.grok_search import GrokFundingEvent

        mock_fetch.return_value = [
            GrokFundingEvent(
                company_name="Fintech BR",
                source_name="grok_live_search",
                amount=30_000_000.0,
                currency="BRL",
                round_type="seed",
                source_url="https://example.com/br",
            ),
        ]

        events = collect_all_sources(
            [self._grok_source()], ProvenanceTracker(), "funding", "test-run"
        )

        assert events[0].amount_local == 30_000_000.0
        assert events[0].amount_usd is None
        assert events[0].currency == "BRL"

    def test_no_results_is_not_an_error(self, mock_fetch, mock_db):
        from apps.agents.funding.collector import collect_all_sources

        mock_fetch.return_value = []

        events = collect_all_sources(
            [self._grok_source()], ProvenanceTracker(), "funding", "test-run"
        )

        assert events == []

    def test_grok_failure_is_isolated(self, mock_fetch, mock_db):
        from apps.agents.funding.collector import collect_all_sources

        mock_fetch.side_effect = RuntimeError("xAI down")

        events = collect_all_sources(
            [self._grok_source()], ProvenanceTracker(), "funding", "test-run"
        )

        assert events == []
