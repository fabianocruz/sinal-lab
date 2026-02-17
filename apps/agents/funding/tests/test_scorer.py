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
