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


def test_sec_skipped_when_no_sec_source():
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


def test_sec_skipped_when_no_initial_events():
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


@patch("apps.agents.sources.sec_form_d.fetch_sec_form_d")
def test_sec_graceful_degradation(mock_fetch_sec):
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
