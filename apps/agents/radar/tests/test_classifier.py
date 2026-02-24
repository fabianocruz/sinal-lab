"""Tests for RADAR classifier module."""

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.radar.collector import TrendSignal
from apps.agents.radar.classifier import (
    ClassifiedSignal,
    classify_topics,
    compute_momentum,
    compute_latam_relevance,
    classify_signals,
)


def make_signal(**kwargs) -> TrendSignal:
    """Helper to create a TrendSignal with defaults."""
    defaults = {
        "title": "Test Signal",
        "url": "https://example.com/test",
        "source_name": "test_source",
        "source_type": "hn",
    }
    defaults.update(kwargs)
    return TrendSignal(**defaults)


class TestClassifyTopics:
    """Test topic classification."""

    def test_ai_ml_topic(self):
        signal = make_signal(title="New machine learning transformer model released")
        topics, primary, confidence = classify_topics(signal)
        assert "ai_ml" in topics
        assert primary == "ai_ml"
        assert confidence > 0

    def test_infrastructure_topic(self):
        signal = make_signal(title="Kubernetes deployment with terraform and docker")
        topics, primary, confidence = classify_topics(signal)
        assert "infrastructure" in topics

    def test_fintech_topic(self):
        signal = make_signal(title="New fintech payment solution using pix and open banking")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics

    def test_developer_tools_topic(self):
        signal = make_signal(title="Rust-based cli package manager for developer experience")
        topics, primary, confidence = classify_topics(signal)
        assert "developer_tools" in topics

    def test_uncategorized(self):
        signal = make_signal(title="Random xyz topic with no matching keywords")
        topics, primary, confidence = classify_topics(signal)
        assert primary == "uncategorized"
        assert confidence == 0.1

    def test_multiple_topics(self):
        signal = make_signal(
            title="AI startup raises seed round venture capital for machine learning platform"
        )
        topics, primary, confidence = classify_topics(signal)
        assert len(topics) >= 2  # Should match ai_ml and startup_ecosystem

    def test_summary_considered(self):
        signal = make_signal(
            title="News",
            summary="Deep learning transformer model for computer vision tasks",
        )
        topics, primary, confidence = classify_topics(signal)
        assert "ai_ml" in topics

    def test_confidence_capped(self):
        signal = make_signal(
            title="machine learning deep learning llm gpt transformer neural network ai agent generative ai"
        )
        _, _, confidence = classify_topics(signal)
        assert confidence <= 1.0

    def test_defi_classified_as_fintech(self):
        signal = make_signal(title="New defi protocol launches stablecoin yield farming on ethereum")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics

    def test_web3_classified_as_fintech(self):
        signal = make_signal(title="web3 wallet smart contract bridge for solana dex")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics
        assert primary == "fintech"

    def test_stablecoin_classified_as_fintech(self):
        signal = make_signal(title="Stablecoin tvl surges amid layer 2 rollup adoption")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics


class TestComputeMomentum:
    """Test momentum scoring."""

    def test_recent_signal_high_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now)
        momentum = compute_momentum(signal, now)
        assert momentum >= 0.5

    def test_old_signal_low_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now - timedelta(days=14))
        momentum = compute_momentum(signal, now)
        assert momentum < 0.5

    def test_no_date_moderate_momentum(self):
        signal = make_signal()
        momentum = compute_momentum(signal)
        assert 0.1 < momentum < 0.8

    def test_github_stars_boost_momentum(self):
        """Stars should increase the engagement component of momentum."""
        now = datetime.now(timezone.utc)
        signal_low_stars = make_signal(
            source_type="github",
            published_at=now,
            metrics={"stars": 1},
        )
        signal_high_stars = make_signal(
            source_type="github",
            published_at=now,
            metrics={"stars": 100000},
        )
        m1 = compute_momentum(signal_low_stars, now)
        m2 = compute_momentum(signal_high_stars, now)
        assert m2 > m1

    def test_momentum_decreases_over_time(self):
        now = datetime.now(timezone.utc)
        scores = []
        for days in [0, 1, 3, 7, 14]:
            signal = make_signal(published_at=now - timedelta(days=days))
            scores.append(compute_momentum(signal, now))
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_momentum_capped_at_one(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(
            published_at=now,
            source_type="trends",
            metrics={"stars": 1_000_000},
        )
        assert compute_momentum(signal, now) <= 1.0


class TestLatamRelevance:
    """Test LATAM relevance scoring."""

    def test_portuguese_content(self):
        signal = make_signal(
            title="Empresa de tecnologia para investimento em mercado de startups"
        )
        score = compute_latam_relevance(signal)
        assert score >= 0.3

    def test_latam_location(self):
        signal = make_signal(title="sao paulo startup ecosystem grows")
        score = compute_latam_relevance(signal)
        assert score >= 0.1

    def test_latam_company(self):
        signal = make_signal(title="Nubank launches new credit product in Brazil")
        score = compute_latam_relevance(signal)
        assert score >= 0.1

    def test_non_latam_content(self):
        signal = make_signal(title="Silicon Valley startup raises Series A")
        score = compute_latam_relevance(signal)
        assert score < 0.3

    def test_score_capped_at_one(self):
        signal = make_signal(
            title="brasil latam america latina sao paulo nubank mercadolibre rappi ifood"
        )
        score = compute_latam_relevance(signal)
        assert score <= 1.0


class TestClassifySignals:
    """Test the full classification pipeline."""

    def test_returns_sorted_by_composite(self):
        signals = [
            make_signal(title="Random news", url="https://a.com/1"),
            make_signal(
                title="AI machine learning startup in latam brasil raises venture capital",
                url="https://a.com/2",
                source_type="hn",
                published_at=datetime.now(timezone.utc),
            ),
            make_signal(title="Weather today", url="https://a.com/3"),
        ]
        classified = classify_signals(signals)
        assert len(classified) == 3
        # Most relevant should be first
        assert classified[0].signal.url == "https://a.com/2"
        # Scores descending
        for i in range(len(classified) - 1):
            assert classified[i].composite_score >= classified[i + 1].composite_score

    def test_empty_input(self):
        assert classify_signals([]) == []

    def test_classified_signal_has_all_fields(self):
        signals = [make_signal(published_at=datetime.now(timezone.utc))]
        classified = classify_signals(signals)
        s = classified[0]
        assert isinstance(s.topics, list)
        assert isinstance(s.primary_topic, str)
        assert 0.0 <= s.topic_confidence <= 1.0
        assert 0.0 <= s.momentum_score <= 1.0
        assert 0.0 <= s.latam_relevance <= 1.0
        assert 0.0 <= s.composite_score <= 1.0
