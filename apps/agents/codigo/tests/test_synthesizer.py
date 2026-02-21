"""Tests for CODIGO synthesizer module."""

import pytest
from datetime import datetime, timezone

from apps.agents.codigo.collector import DevSignal
from apps.agents.codigo.analyzer import AnalyzedSignal
from apps.agents.codigo.synthesizer import (
    select_top_signals,
    group_by_category,
    synthesize_dev_report,
)


def make_analyzed(
    title: str = "test/repo",
    url: str = "https://github.com/test/repo",
    source_name: str = "github_trending_daily",
    category: str = "ai_frameworks",
    language: str = "python",
    momentum_score: float = 0.5,
    community_score: float = 0.5,
    summary: str = "A test repo.",
    **kwargs,
) -> AnalyzedSignal:
    """Helper to create an AnalyzedSignal with defaults."""
    signal = DevSignal(
        title=title,
        url=url,
        source_name=source_name,
        signal_type="repo",
        summary=summary,
        language=language,
        published_at=datetime.now(timezone.utc),
        **kwargs,
    )
    return AnalyzedSignal(
        signal=signal,
        category=category,
        language_weight=0.9 if language == "python" else 0.5,
        momentum_score=momentum_score,
        community_score=community_score,
        adoption_indicator="rising",
    )


class TestSelectTopSignals:
    """Test top signal selection."""

    def test_selects_top_n(self):
        signals = [
            make_analyzed(
                url=f"https://x.com/{i}",
                source_name=f"source_{i % 10}",
                momentum_score=1.0 - i * 0.02,
            )
            for i in range(30)
        ]
        selected = select_top_signals(signals, count=10)
        assert len(selected) == 10

    def test_source_diversity(self):
        signals = [
            make_analyzed(
                url=f"https://x.com/{i}",
                source_name="same_source",
                momentum_score=0.9,
            )
            for i in range(15)
        ]
        selected = select_top_signals(signals, count=10)
        assert len(selected) == 4

    def test_filters_low_score(self):
        signals = [
            make_analyzed(url="https://x.com/1", momentum_score=0.8, community_score=0.8),
            make_analyzed(url="https://x.com/2", momentum_score=0.01, community_score=0.01, language=None),
            make_analyzed(url="https://x.com/3", momentum_score=0.6, community_score=0.6),
        ]
        # Signal 2 composite: 0.5*0.2 + 0.01*0.4 + 0.01*0.4 = 0.108
        # Use a higher threshold to filter it
        selected = select_top_signals(signals, min_score=0.15)
        assert len(selected) == 2

    def test_empty_input(self):
        assert select_top_signals([]) == []


class TestGroupByCategory:
    """Test grouping by category."""

    def test_groups_correctly(self):
        signals = [
            make_analyzed(url="https://x.com/1", category="ai_frameworks"),
            make_analyzed(url="https://x.com/2", category="web_frameworks"),
            make_analyzed(url="https://x.com/3", category="ai_frameworks"),
        ]
        sections = group_by_category(signals)
        assert len(sections) == 2
        total = sum(len(s.signals) for s in sections)
        assert total == 3

    def test_general_last(self):
        signals = [
            make_analyzed(url="https://x.com/1", category="general"),
            make_analyzed(url="https://x.com/2", category="ai_frameworks"),
        ]
        sections = group_by_category(signals)
        assert sections[-1].category_key == "general"

    def test_empty_input(self):
        assert group_by_category([]) == []


class TestSynthesizeDevReport:
    """Test full dev report synthesis."""

    def test_generates_valid_markdown(self):
        signals = [
            make_analyzed(
                title=f"org/repo-{i}",
                url=f"https://x.com/{i}",
                source_name=f"source_{i % 5}",
                momentum_score=0.9 - i * 0.02,
            )
            for i in range(20)
        ]
        report = synthesize_dev_report(signals, week_number=3)
        assert "# CODIGO Semanal" in report
        assert "Semana 3" in report
        assert "CODIGO" in report
        assert "---" in report

    def test_includes_signals(self):
        signals = [
            make_analyzed(
                title="vercel/next.js",
                url="https://github.com/vercel/next.js",
                momentum_score=0.9,
                community_score=0.9,
            ),
        ]
        report = synthesize_dev_report(signals)
        assert "vercel/next.js" in report
        assert "https://github.com/vercel/next.js" in report

    def test_includes_methodology(self):
        signals = [make_analyzed(momentum_score=0.8, community_score=0.8)]
        report = synthesize_dev_report(signals)
        assert "Metodologia" in report
        assert "Sinal.lab" in report

    def test_empty_signals(self):
        report = synthesize_dev_report([])
        assert "# CODIGO Semanal" in report
        assert "0 sinais" in report

    def test_date_formatting(self):
        signals = [make_analyzed(momentum_score=0.8, community_score=0.8)]
        date = datetime(2026, 2, 17, tzinfo=timezone.utc)
        report = synthesize_dev_report(signals, report_date=date)
        assert "17/02/2026" in report

    def test_language_summary(self):
        signals = [
            make_analyzed(url=f"https://x.com/{i}", language="python", momentum_score=0.8, community_score=0.8)
            for i in range(5)
        ]
        report = synthesize_dev_report(signals)
        assert "python" in report.lower()
