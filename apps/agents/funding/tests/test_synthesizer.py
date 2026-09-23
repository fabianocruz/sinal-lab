"""Tests for FUNDING agent synthesizer."""

import pytest
from datetime import date

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.funding.collector import FundingEvent
from apps.agents.funding.scorer import ScoredFundingEvent
from apps.agents.funding.synthesizer import (
    MIN_SCORE_FOR_REPORT,
    filter_reportable,
    format_amount,
    format_round_type,
    is_large_round,
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


def _scored(name: str, round_type: str, amount_usd, score: float = 0.6) -> ScoredFundingEvent:
    event = FundingEvent(
        company_name=name,
        company_slug=name.lower(),
        round_type=round_type,
        amount_usd=amount_usd,
        announced_date=date(2026, 9, 9),
        source_url=f"https://example.com/{name.lower()}",
        source_name="crunchbase_manual_dump",
    )
    confidence = ConfidenceScore(data_quality=score, analysis_confidence=score)
    return ScoredFundingEvent(event=event, confidence=confidence, composite_score=score)


def test_is_large_round_handles_absolute_and_millions():
    assert is_large_round(125_000_000) is True      # absolute USD
    assert is_large_round(125.0) is True            # legacy millions
    assert is_large_round(126_471) is False         # $126K pre-seed
    assert is_large_round(3.7) is False             # legacy $3.7M
    assert is_large_round(5_000_000) is True        # exactly the threshold
    assert is_large_round(None) is False


def test_filter_reportable_uses_min_score():
    kept = _scored("Kept", "seed", 1_000_000, score=MIN_SCORE_FOR_REPORT)
    dropped = _scored("Dropped", "seed", 1_000_000, score=MIN_SCORE_FOR_REPORT - 0.01)
    assert filter_reportable([kept, dropped]) == [kept]


def test_sections_group_by_normalized_amount():
    """Absolute-USD amounts must not all land in the Series A+ bucket."""
    events = [
        _scored("Kapital", "series_c", 125_000_000),
        _scored("Ginastee", "pre_seed", 126_471),
        _scored("Doroth", "venture", 4_437_242),
        _scored("Bull", "seed", 3.7),  # legacy millions format
    ]
    report = synthesize_funding_report(events, week_number=38, writer=None)

    series_a_plus = report.split("## Series A+")[1].split("## ")[0]
    seed_section = report.split("## Seed & Pre-Seed")[1].split("## ")[0]
    other_section = report.split("## Outros Investimentos")[1].split("---")[0]

    assert "Kapital" in series_a_plus
    assert "Ginastee" not in series_a_plus and "Bull" not in series_a_plus
    assert "Ginastee" in seed_section and "Bull" in seed_section
    assert "Doroth" in other_section


def test_template_intro_total_is_in_millions_after_normalization():
    events = [_scored("Kapital", "series_c", 125_000_000), _scored("Bull", "seed", 3.7)]
    report = synthesize_funding_report(events, week_number=38, writer=None)
    assert "somando US$ 128.7M" in report
