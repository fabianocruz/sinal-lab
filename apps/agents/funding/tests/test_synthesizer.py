"""Tests for FUNDING agent synthesizer."""

import pytest
from datetime import date

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.scorer import ScoredFundingEvent
from apps.agents.funding.synthesizer import (
    format_amount,
    format_round_type,
    synthesize_funding_report,
)


def test_format_amount_millions():
    """Test amount formatting for values >= $1M."""
    assert format_amount(10.0) == "$10.0M"
    assert format_amount(150.5) == "$150.5M"


def test_format_amount_thousands():
    """Test amount formatting for values < $1M."""
    assert format_amount(0.5) == "$500K"
    assert format_amount(0.25) == "$250K"


def test_format_amount_none():
    """Test amount formatting when amount is None."""
    assert format_amount(None) == "Valor não divulgado"


def test_format_round_type():
    """Test round type formatting."""
    assert format_round_type("series_a") == "Série A"
    assert format_round_type("series_b") == "Série B"
    assert format_round_type("seed") == "Seed"
    assert format_round_type("pre_seed") == "Pre-Seed"
    assert format_round_type("ipo") == "IPO"


def test_synthesize_funding_report():
    """Test synthesizing a complete funding report."""
    event1 = FundingEvent(
        company_name="Big Corp",
        round_type="series_a",
        source_url="http://test.com/1",
        source_name="test",
        amount_usd=50.0,
        announced_date=date.today(),
        lead_investors=["Kaszek Ventures"],
    )

    event2 = FundingEvent(
        company_name="Small Startup",
        round_type="seed",
        source_url="http://test.com/2",
        source_name="test",
        amount_usd=2.0,
        announced_date=date.today(),
    )

    confidence1 = ConfidenceScore(data_quality=0.8, analysis_confidence=0.75)
    confidence2 = ConfidenceScore(data_quality=0.6, analysis_confidence=0.55)

    scored = [
        ScoredFundingEvent(event=event1, confidence=confidence1, composite_score=0.775),
        ScoredFundingEvent(event=event2, confidence=confidence2, composite_score=0.575),
    ]

    report = synthesize_funding_report(scored, week_number=7)

    # Verify report structure
    assert "Investimentos LATAM" in report
    assert "Semana 7/2026" in report
    assert "Big Corp" in report
    assert "Small Startup" in report
    assert "$50.0M" in report
    assert "Série A" in report
    assert "Seed" in report
    assert "Kaszek Ventures" in report


def test_synthesize_empty_report():
    """Test synthesizing report with no events."""
    report = synthesize_funding_report([], week_number=7)

    assert "Sem rodadas relevantes" in report or "Nenhuma rodada" in report
