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
