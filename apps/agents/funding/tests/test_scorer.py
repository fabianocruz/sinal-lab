"""Tests for FUNDING agent scorer."""

import pytest
from datetime import date, timedelta

from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.scorer import score_single_event


def test_score_event_with_amount():
    """Test scoring event with valid amount."""
    event = FundingEvent(
        company_name="Test Co",
        round_type="series_a",
        source_url="http://test.com",
        source_name="test_source",
        amount_usd=10.0,
        announced_date=date.today(),
    )

    scored = score_single_event(event, date.today())

    assert scored.confidence.data_quality > 0.3
    assert scored.composite_score > 0


def test_score_event_without_amount():
    """Test scoring event without amount (penalty)."""
    event = FundingEvent(
        company_name="Test Co",
        round_type="seed",
        source_url="http://test.com",
        source_name="test_source",
        amount_usd=None,
        announced_date=date.today(),
    )

    scored = score_single_event(event, date.today())

    # Should have lower score due to missing amount
    assert scored.confidence.data_quality < 0.8


def test_score_event_with_conflict():
    """Test scoring event with amount conflict."""
    event = FundingEvent(
        company_name="Test Co",
        round_type="series_a",
        source_url="http://test.com",
        source_name="test_source",
        amount_usd=10.0,
        notes="[AMOUNT_CONFLICT: 2 sources report different amounts]",
        announced_date=date.today(),
    )

    scored = score_single_event(event, date.today())

    # Should have reduced confidence due to conflict
    assert scored.confidence.data_quality < 0.7


def test_score_old_event():
    """Test scoring event with old announcement date."""
    old_date = date.today() - timedelta(days=90)

    event = FundingEvent(
        company_name="Test Co",
        round_type="seed",
        source_url="http://test.com",
        source_name="test_source",
        amount_usd=5.0,
        announced_date=old_date,
    )

    scored = score_single_event(event, date.today())

    # Should have reduced score due to age
    assert scored.confidence.data_quality < 0.9


# --- Cross-Reference Verification Tests ---

from apps.agents.funding.scorer import apply_cross_ref_verification, ScoredFundingEvent
from apps.agents.base.confidence import ConfidenceScore


def test_sec_sourced_event_gets_regulatory_floor():
    """SEC-sourced events get DQ floor of 0.85 (REGULATORY)."""
    event = FundingEvent(
        company_name="Nubank Capital LLC",
        round_type="unknown",
        source_url="https://www.sec.gov/cgi-bin/browse-edgar?CIK=123",
        source_name="sec_form_d",
        amount_usd=750.0,
        announced_date=date.today(),
    )
    scored = ScoredFundingEvent(
        event=event,
        confidence=ConfidenceScore(data_quality=0.3, analysis_confidence=0.27),
        composite_score=0.0,  # Will be recalculated
    )

    result = apply_cross_ref_verification([scored])

    assert result[0].confidence.data_quality >= 0.85
    assert result[0].confidence.verified is True


def test_cross_ref_confirmed_event_gets_boost():
    """Events confirmed by SEC cross-ref get +0.1 confidence boost."""
    # SEC event
    sec_event = FundingEvent(
        company_name="Nubank",
        round_type="unknown",
        source_url="https://sec.gov/nubank",
        source_name="sec_form_d",
        amount_usd=750.0,
        announced_date=date.today(),
    )
    sec_scored = ScoredFundingEvent(
        event=sec_event,
        confidence=ConfidenceScore(data_quality=0.3, analysis_confidence=0.27),
        composite_score=0.0,
    )

    # RSS event for same company
    rss_event = FundingEvent(
        company_name="Nubank",
        round_type="series_g",
        source_url="https://example.com/nubank",
        source_name="crunchbase_news",
        amount_usd=750.0,
        announced_date=date.today(),
    )
    rss_scored = ScoredFundingEvent(
        event=rss_event,
        confidence=ConfidenceScore(data_quality=0.4, analysis_confidence=0.36),
        composite_score=0.0,
    )

    result = apply_cross_ref_verification([sec_scored, rss_scored])

    # Find the RSS event in results
    rss_result = [r for r in result if r.event.source_name == "crunchbase_news"][0]
    # Should have boost: 0.4 + 0.1 = 0.5
    assert rss_result.confidence.data_quality >= 0.49  # Allow for rounding


def test_cross_ref_contradicted_event_gets_penalty():
    """Events with amount contradiction get -0.15 penalty."""
    sec_event = FundingEvent(
        company_name="TestCo",
        round_type="unknown",
        source_url="https://sec.gov/testco",
        source_name="sec_form_d",
        amount_usd=100.0,  # Very different from RSS
        announced_date=date.today(),
    )
    sec_scored = ScoredFundingEvent(
        event=sec_event,
        confidence=ConfidenceScore(data_quality=0.3, analysis_confidence=0.27),
        composite_score=0.0,
    )

    rss_event = FundingEvent(
        company_name="TestCo",
        round_type="series_a",
        source_url="https://example.com/testco",
        source_name="startupi",
        amount_usd=10.0,  # 10x difference -> >30% -> contradiction
        announced_date=date.today(),
    )
    rss_scored = ScoredFundingEvent(
        event=rss_event,
        confidence=ConfidenceScore(data_quality=0.5, analysis_confidence=0.45),
        composite_score=0.0,
    )

    result = apply_cross_ref_verification([sec_scored, rss_scored])

    rss_result = [r for r in result if r.event.source_name == "startupi"][0]
    # Should have penalty: 0.5 - 0.15 = 0.35
    assert rss_result.confidence.data_quality <= 0.36


def test_cross_ref_unconfirmed_event_unchanged():
    """Events with no SEC match have unchanged confidence."""
    rss_event = FundingEvent(
        company_name="UnknownCo",
        round_type="seed",
        source_url="https://example.com/unknown",
        source_name="startupi",
        amount_usd=5.0,
        announced_date=date.today(),
    )
    original_dq = 0.4
    rss_scored = ScoredFundingEvent(
        event=rss_event,
        confidence=ConfidenceScore(data_quality=original_dq, analysis_confidence=0.36),
        composite_score=0.0,
    )

    # No SEC events -> no cross-ref data
    result = apply_cross_ref_verification([rss_scored])

    assert result[0].confidence.data_quality == original_dq


def test_backward_compatible_without_sec_filings():
    """Scoring is unchanged when no SEC data is available."""
    events = [
        FundingEvent(
            company_name=f"Company{i}",
            round_type="series_a",
            source_url=f"https://example.com/{i}",
            source_name="crunchbase_news",
            amount_usd=10.0 * (i + 1),
            announced_date=date.today(),
        )
        for i in range(3)
    ]

    scored = [
        ScoredFundingEvent(
            event=e,
            confidence=ConfidenceScore(data_quality=0.4, analysis_confidence=0.36),
            composite_score=0.0,
        )
        for e in events
    ]

    result = apply_cross_ref_verification(scored)

    # All events should have same DQ since no SEC cross-ref
    for r in result:
        assert r.confidence.data_quality == 0.4
