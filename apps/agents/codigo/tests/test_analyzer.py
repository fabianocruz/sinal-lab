"""Tests for CODIGO analyzer module."""

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.codigo.collector import DevSignal
from apps.agents.codigo.analyzer import (
    AnalyzedSignal,
    categorize_signal,
    compute_language_weight,
    compute_momentum,
    compute_community_score,
    determine_adoption,
    analyze_signals,
)


def make_signal(**kwargs) -> DevSignal:
    """Helper to create a DevSignal with defaults."""
    defaults = {
        "title": "test/repo",
        "url": "https://github.com/test/repo",
        "source_name": "github_trending_daily",
        "signal_type": "repo",
    }
    defaults.update(kwargs)
    return DevSignal(**defaults)


class TestCategorizeSignal:
    """Test dev signal categorization."""

    def test_ai_frameworks(self):
        signal = make_signal(title="New machine learning langchain llm framework")
        assert categorize_signal(signal) == "ai_frameworks"

    def test_web_frameworks(self):
        signal = make_signal(title="Next.js react framework update with tailwind")
        assert categorize_signal(signal) == "web_frameworks"

    def test_developer_tools(self):
        signal = make_signal(title="New cli linter and formatter tool")
        assert categorize_signal(signal) == "developer_tools"

    def test_infrastructure(self):
        signal = make_signal(title="Kubernetes terraform docker deployment tool")
        assert categorize_signal(signal) == "infrastructure"

    def test_databases(self):
        signal = make_signal(title="Vector database with postgres and redis support")
        assert categorize_signal(signal) == "databases"

    def test_general_fallback(self):
        signal = make_signal(title="Random project xyz")
        assert categorize_signal(signal) == "general"


class TestComputeLanguageWeight:
    """Test language weight scoring."""

    def test_python_high(self):
        signal = make_signal(language="python")
        assert compute_language_weight(signal) == 0.9

    def test_typescript_high(self):
        signal = make_signal(language="TypeScript")
        assert compute_language_weight(signal) == 0.9

    def test_rust_high(self):
        signal = make_signal(language="Rust")
        assert compute_language_weight(signal) == 0.85

    def test_unknown_language(self):
        signal = make_signal(language="brainfuck")
        assert compute_language_weight(signal) == 0.3

    def test_no_language_uses_tags(self):
        signal = make_signal(language=None, tags=["python", "ai"])
        assert compute_language_weight(signal) == 0.9

    def test_no_language_no_tags(self):
        signal = make_signal(language=None, tags=[])
        assert compute_language_weight(signal) == 0.3


class TestComputeMomentum:
    """Test momentum scoring."""

    def test_recent_high_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now)
        assert compute_momentum(signal, now) >= 0.3

    def test_old_low_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now - timedelta(days=14))
        assert compute_momentum(signal, now) < 0.3

    def test_stars_boost(self):
        now = datetime.now(timezone.utc)
        signal_low = make_signal(published_at=now, metrics={"stars": 1, "forks": 0})
        signal_high = make_signal(published_at=now, metrics={"stars": 100000, "forks": 5000})
        assert compute_momentum(signal_high, now) > compute_momentum(signal_low, now)

    def test_no_date(self):
        signal = make_signal()
        momentum = compute_momentum(signal)
        assert 0.0 < momentum < 0.8

    def test_capped_at_one(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(
            published_at=now,
            metrics={"stars": 1_000_000, "forks": 500_000},
        )
        assert compute_momentum(signal, now) <= 1.0


class TestCommunityScore:
    """Test community score computation."""

    def test_high_stars(self):
        signal = make_signal(metrics={"stars": 5000, "forks": 500, "open_issues": 100})
        score = compute_community_score(signal)
        assert score >= 0.5

    def test_low_metrics(self):
        signal = make_signal(metrics={"stars": 5, "forks": 1})
        score = compute_community_score(signal)
        assert score < 0.3

    def test_package_base_score(self):
        signal = make_signal(signal_type="package", metrics={})
        score = compute_community_score(signal)
        assert score >= 0.3

    def test_capped_at_one(self):
        signal = make_signal(
            metrics={"stars": 200000, "forks": 50000, "open_issues": 5000, "watchers": 5000}
        )
        assert compute_community_score(signal) <= 1.0


class TestDetermineAdoption:
    """Test adoption trajectory classification."""

    def test_new_repo(self):
        signal = make_signal(metrics={"stars": 20, "forks": 2})
        assert determine_adoption(signal) == "new"

    def test_rising_repo(self):
        signal = make_signal(metrics={"stars": 500, "forks": 50})
        assert determine_adoption(signal) == "rising"

    def test_stable_high_stars(self):
        signal = make_signal(metrics={"stars": 50000, "forks": 3000})
        assert determine_adoption(signal) == "stable"

    def test_package_is_stable(self):
        signal = make_signal(signal_type="package", metrics={})
        assert determine_adoption(signal) == "stable"


class TestAnalyzeSignals:
    """Test the full analysis pipeline."""

    def test_returns_sorted(self):
        signals = [
            make_signal(title="Random repo", url="https://x.com/1"),
            make_signal(
                title="AI machine learning langchain llm framework",
                url="https://x.com/2",
                language="python",
                published_at=datetime.now(timezone.utc),
                metrics={"stars": 10000, "forks": 1000},
            ),
            make_signal(title="Misc tool", url="https://x.com/3"),
        ]
        analyzed = analyze_signals(signals)
        assert len(analyzed) == 3
        assert analyzed[0].signal.url == "https://x.com/2"
        for i in range(len(analyzed) - 1):
            assert analyzed[i].composite_score >= analyzed[i + 1].composite_score

    def test_empty_input(self):
        assert analyze_signals([]) == []

    def test_analyzed_has_all_fields(self):
        signals = [make_signal(published_at=datetime.now(timezone.utc), language="python")]
        analyzed = analyze_signals(signals)
        a = analyzed[0]
        assert isinstance(a.category, str)
        assert 0.0 <= a.language_weight <= 1.0
        assert 0.0 <= a.momentum_score <= 1.0
        assert 0.0 <= a.community_score <= 1.0
        assert a.adoption_indicator in ("new", "rising", "stable", "declining")
        assert 0.0 <= a.composite_score <= 1.0
