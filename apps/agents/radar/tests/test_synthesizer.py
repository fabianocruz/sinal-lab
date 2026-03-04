"""Tests for RADAR synthesizer module."""

import pytest
from datetime import datetime, timezone

from apps.agents.radar.collector import TrendSignal
from apps.agents.radar.classifier import ClassifiedSignal
from apps.agents.radar.synthesizer import (
    momentum_indicator,
    select_top_signals,
    group_by_topic,
    synthesize_trend_report,
)


def make_classified(
    title: str = "Test Signal",
    url: str = "https://example.com/test",
    source_name: str = "test_source",
    primary_topic: str = "ai_ml",
    topic_confidence: float = 0.5,
    momentum_score: float = 0.5,
    latam_relevance: float = 0.3,
    summary: str = "A test signal summary.",
    **kwargs,
) -> ClassifiedSignal:
    """Helper to create a ClassifiedSignal with defaults."""
    signal = TrendSignal(
        title=title,
        url=url,
        source_name=source_name,
        source_type="hn",
        summary=summary,
        published_at=datetime.now(timezone.utc),
        **kwargs,
    )
    return ClassifiedSignal(
        signal=signal,
        topics=[primary_topic],
        primary_topic=primary_topic,
        topic_confidence=topic_confidence,
        momentum_score=momentum_score,
        latam_relevance=latam_relevance,
    )


class TestMomentumIndicator:
    """Test momentum indicator text."""

    def test_forte(self):
        assert momentum_indicator(0.9) == "[FORTE]"

    def test_medio(self):
        assert momentum_indicator(0.6) == "[MEDIO]"

    def test_leve(self):
        assert momentum_indicator(0.4) == "[LEVE]"

    def test_fraco(self):
        assert momentum_indicator(0.1) == "[FRACO]"


class TestSelectTopSignals:
    """Test top signal selection with diversity."""

    def test_selects_top_n(self):
        signals = [
            make_classified(
                url=f"https://x.com/{i}",
                source_name=f"source_{i % 10}",
                momentum_score=1.0 - i * 0.02,
            )
            for i in range(30)
        ]
        selected = select_top_signals(signals, count=10)
        assert len(selected) == 10

    def test_source_diversity(self):
        """No more than 4 items from the same source."""
        signals = [
            make_classified(
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
            make_classified(url="https://x.com/1", momentum_score=0.8),
            make_classified(url="https://x.com/2", momentum_score=0.01, topic_confidence=0.01, latam_relevance=0.01),
            make_classified(url="https://x.com/3", momentum_score=0.6),
        ]
        selected = select_top_signals(signals, count=10, min_score=0.10)
        assert len(selected) == 2

    def test_empty_input(self):
        assert select_top_signals([]) == []

    def test_entity_frequency_cap(self):
        """No more than MAX_PER_ENTITY items about the same company."""
        signals = [
            make_classified(
                title=f"EFEX raises ${i}M in round {i}",
                url=f"https://source{i}.com/efex-{i}",
                source_name=f"source_{i}",
                momentum_score=0.9 - i * 0.01,
            )
            for i in range(6)
        ]
        selected = select_top_signals(signals, count=10)
        assert len(selected) == 2

    def test_entity_cap_different_entities_unaffected(self):
        """Entity cap for one company doesn't block others."""
        signals = [
            make_classified(title="EFEX raises $5M", url="https://a.com/1", source_name="s1", momentum_score=0.9),
            make_classified(title="EFEX closes round", url="https://b.com/2", source_name="s2", momentum_score=0.89),
            make_classified(title="EFEX gets funding", url="https://c.com/3", source_name="s3", momentum_score=0.88),
            make_classified(title="KAVAK raises $300M", url="https://d.com/4", source_name="s4", momentum_score=0.87),
        ]
        selected = select_top_signals(signals, count=10)
        titles = [s.signal.title for s in selected]
        assert len(selected) == 3  # 2 EFEX + 1 KAVAK
        assert sum(1 for t in titles if "EFEX" in t) == 2

    def test_entity_cap_with_source_cap_combined(self):
        """Both caps apply simultaneously."""
        signals = [
            make_classified(title="EFEX article 1", url="https://x.com/1", source_name="same", momentum_score=0.9),
            make_classified(title="EFEX article 2", url="https://x.com/2", source_name="same", momentum_score=0.89),
            make_classified(title="EFEX article 3", url="https://x.com/3", source_name="same", momentum_score=0.88),
            make_classified(title="KAVAK news", url="https://y.com/4", source_name="other", momentum_score=0.87),
        ]
        selected = select_top_signals(signals, count=10)
        assert len(selected) == 3  # 2 EFEX (entity cap) + 1 KAVAK


class TestGroupByTopic:
    """Test grouping signals by topic."""

    def test_groups_by_topic(self):
        signals = [
            make_classified(title="AI signal", url="https://x.com/1", primary_topic="ai_ml"),
            make_classified(title="Fintech signal", url="https://x.com/2", primary_topic="fintech"),
            make_classified(title="AI signal 2", url="https://x.com/3", primary_topic="ai_ml"),
        ]
        sections = group_by_topic(signals)
        assert len(sections) == 2
        total = sum(len(s.signals) for s in sections)
        assert total == 3

    def test_uncategorized_last(self):
        signals = [
            make_classified(url="https://x.com/1", primary_topic="uncategorized"),
            make_classified(url="https://x.com/2", primary_topic="ai_ml"),
        ]
        sections = group_by_topic(signals)
        assert sections[-1].topic_key == "uncategorized"

    def test_empty_input(self):
        assert group_by_topic([]) == []


class TestSynthesizeTrendReport:
    """Test full trend report synthesis."""

    def test_generates_valid_markdown(self):
        signals = [
            make_classified(
                title=f"Signal {i}",
                url=f"https://x.com/{i}",
                source_name=f"source_{i % 5}",
                momentum_score=0.9 - i * 0.02,
            )
            for i in range(20)
        ]
        report = synthesize_trend_report(signals, week_number=7)
        assert "# RADAR Semanal" in report
        assert "Semana 7" in report
        assert "RADAR" in report
        assert "---" in report

    def test_includes_signals(self):
        signals = [
            make_classified(
                title="Important AI Discovery",
                url="https://example.com/ai",
                momentum_score=0.9,
            ),
        ]
        report = synthesize_trend_report(signals)
        assert "Important AI Discovery" in report
        assert "https://example.com/ai" in report

    def test_includes_methodology_footer(self):
        signals = [make_classified(momentum_score=0.8)]
        report = synthesize_trend_report(signals)
        assert "Metodologia" in report
        assert "Sinal.lab" in report

    def test_empty_signals(self):
        report = synthesize_trend_report([])
        assert "# RADAR Semanal" in report
        assert "0 sinais" in report

    def test_report_date_formatting(self):
        signals = [make_classified(momentum_score=0.8)]
        date = datetime(2026, 2, 17, tzinfo=timezone.utc)
        report = synthesize_trend_report(signals, report_date=date)
        assert "17/02/2026" in report
