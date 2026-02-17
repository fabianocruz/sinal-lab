"""Tests for FUNDING agent database writer."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.db_writer import upsert_funding_round, update_company_funding_stats


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = Mock()
    session.query = Mock(return_value=Mock())
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def sample_funding_event():
    """Sample FundingEvent for testing."""
    return FundingEvent(
        company_name="Test Startup",
        company_slug="test-startup",
        round_type="series_a",
        amount_usd=10.0,
        currency="USD",
        announced_date=date(2026, 2, 15),
        lead_investors=["VC Fund A"],
        source_url="https://test.com/article",
        source_name="test_source",
    )


def test_upsert_funding_round_new_record(mock_session, sample_funding_event):
    """Test inserting new funding round."""
    # Mock: no existing record
    mock_session.query().filter_by().first.return_value = None

    result = upsert_funding_round(mock_session, sample_funding_event, confidence=0.8)

    # Should add new record
    assert mock_session.add.called
    assert mock_session.commit.called


def test_upsert_funding_round_update_higher_confidence(mock_session, sample_funding_event):
    """Test updating existing record with higher confidence."""
    # Mock existing record with lower confidence
    existing = MagicMock()
    existing.confidence = 0.5
    existing.company_name = "Test Startup"
    mock_session.query().filter_by().first.return_value = existing

    result = upsert_funding_round(mock_session, sample_funding_event, confidence=0.8)

    # Should update existing record
    assert existing.amount_usd == 10.0
    assert existing.confidence == 0.8
    assert mock_session.commit.called


def test_upsert_funding_round_skip_lower_confidence(mock_session, sample_funding_event):
    """Test skipping update when existing confidence is higher."""
    # Mock existing record with higher confidence
    existing = MagicMock()
    existing.confidence = 0.9
    existing.company_name = "Test Startup"
    mock_session.query().filter_by().first.return_value = existing

    result = upsert_funding_round(mock_session, sample_funding_event, confidence=0.7)

    # Should NOT update (confidence lower)
    assert existing.confidence == 0.9  # Unchanged
    assert result == existing


def test_upsert_funding_round_without_slug(mock_session):
    """Test handling event without company_slug."""
    event = FundingEvent(
        company_name="No Slug Company",
        company_slug=None,  # Missing slug
        round_type="seed",
        amount_usd=5.0,
        source_url="https://test.com",
        source_name="test",
        announced_date=date(2026, 2, 15),
    )

    mock_session.query().filter_by().first.return_value = None

    result = upsert_funding_round(mock_session, event, confidence=0.6)

    # Should still create record with fallback slug
    assert mock_session.add.called


def test_update_company_funding_stats(mock_session):
    """Test updating company metadata with funding stats."""
    # Mock company
    company = MagicMock()
    company.metadata_ = {}
    mock_session.query().filter_by().first.return_value = company

    # Mock funding rounds
    round1 = MagicMock()
    round1.announced_date = date(2026, 1, 15)
    round1.amount_usd = 5.0

    round2 = MagicMock()
    round2.announced_date = date(2026, 2, 15)
    round2.amount_usd = 10.0

    mock_session.query().filter_by().all.return_value = [round1, round2]

    update_company_funding_stats(mock_session, "test-company")

    # Should update metadata
    assert "last_funding_date" in company.metadata_
    assert company.metadata_["total_raised_usd"] == 15.0
    assert company.metadata_["funding_rounds_count"] == 2
    assert mock_session.commit.called


def test_update_company_funding_stats_no_company(mock_session):
    """Test handling missing company."""
    mock_session.query().filter_by().first.return_value = None

    # Should not crash
    update_company_funding_stats(mock_session, "nonexistent-company")

    # Should not commit (no company found)
    assert not mock_session.commit.called
