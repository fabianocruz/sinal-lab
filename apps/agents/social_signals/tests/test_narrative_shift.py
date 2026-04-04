"""Tests for Social Signals narrative shift detection."""

import pytest

from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SignalDimensions,
    SocialPost,
)
from apps.agents.social_signals.narrative_shift import (
    SCORE_DELTA_THRESHOLD,
    detect_narrative_shifts,
    summarize_shifts,
)


def _make_cluster(
    name: str = "Test Cluster",
    theme: str = "AI",
    composite_score: float = 0.5,
    narrative_stage: str = "accelerating",
    signal_count: int = 5,
) -> SignalClusterResult:
    """Create a SignalClusterResult with controlled composite score."""
    dims = SignalDimensions(
        volume=composite_score,
        velocity=composite_score,
        authority_concentration=composite_score,
        cross_platform_propagation=composite_score,
        sentiment_shift=composite_score,
        new_entrants=composite_score,
        narrative_maturity=composite_score,
        commercial_signals=composite_score,
    )
    signals = []
    for i in range(signal_count):
        post = SocialPost(
            text=f"signal {i}",
            url=f"https://example.com/{i}",
            platform="twitter",
        )
        signals.append(ProcessedSignal(post=post, theme=theme))

    return SignalClusterResult(
        name=name,
        theme=theme,
        signals=signals,
        dimensions=dims,
        narrative_stage=narrative_stage,
    )


class TestDetectNarrativeShifts:
    def test_empty_current_clusters(self):
        shifts = detect_narrative_shifts([], [_make_cluster()])
        assert shifts == []

    def test_no_previous_clusters_all_new(self):
        clusters = [
            _make_cluster(name="A", theme="AI"),
            _make_cluster(name="B", theme="Fintech"),
        ]
        shifts = detect_narrative_shifts(clusters, None)
        assert len(shifts) == 2
        assert all(s["type"] == "new_narrative" for s in shifts)

    def test_empty_previous_clusters_all_new(self):
        clusters = [_make_cluster(name="A", theme="AI")]
        shifts = detect_narrative_shifts(clusters, [])
        assert len(shifts) == 1
        assert shifts[0]["type"] == "new_narrative"

    def test_new_narrative_detected(self):
        current = [_make_cluster(name="AI Agents", theme="AI")]
        previous = [_make_cluster(name="Fintech Payments", theme="Fintech")]
        shifts = detect_narrative_shifts(current, previous)
        assert len(shifts) == 1
        assert shifts[0]["type"] == "new_narrative"
        assert shifts[0]["cluster"] == "AI Agents"

    def test_acceleration_detected(self):
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.6)]
        previous = [_make_cluster(name="AI prev", theme="AI", composite_score=0.3)]
        shifts = detect_narrative_shifts(current, previous)
        assert len(shifts) == 1
        assert shifts[0]["type"] == "acceleration"
        assert shifts[0]["score_delta"] > 0

    def test_deceleration_detected(self):
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.2)]
        previous = [_make_cluster(name="AI prev", theme="AI", composite_score=0.5)]
        shifts = detect_narrative_shifts(current, previous)
        assert len(shifts) == 1
        assert shifts[0]["type"] == "deceleration"
        assert shifts[0]["score_delta"] < 0

    def test_no_shift_within_threshold(self):
        """Small score changes should not be classified as shifts."""
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.5)]
        previous = [_make_cluster(name="AI", theme="AI", composite_score=0.45)]
        shifts = detect_narrative_shifts(current, previous)
        assert len(shifts) == 0

    def test_custom_threshold(self):
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.55)]
        previous = [_make_cluster(name="AI", theme="AI", composite_score=0.5)]
        # Default threshold 0.1: no shift
        shifts = detect_narrative_shifts(current, previous, score_delta_threshold=0.1)
        assert len(shifts) == 0
        # Lower threshold 0.01: acceleration detected
        shifts = detect_narrative_shifts(current, previous, score_delta_threshold=0.01)
        assert len(shifts) == 1
        assert shifts[0]["type"] == "acceleration"

    def test_mixed_shifts(self):
        current = [
            _make_cluster(name="AI Agents", theme="AI", composite_score=0.7),
            _make_cluster(name="Fintech", theme="Fintech", composite_score=0.2),
            _make_cluster(name="DeFi", theme="DeFi", composite_score=0.5),
        ]
        previous = [
            _make_cluster(name="AI prev", theme="AI", composite_score=0.3),
            _make_cluster(name="Fintech prev", theme="Fintech", composite_score=0.5),
        ]
        shifts = detect_narrative_shifts(current, previous)

        types = {s["type"] for s in shifts}
        assert "acceleration" in types  # AI: 0.3 -> 0.7
        assert "deceleration" in types  # Fintech: 0.5 -> 0.2
        assert "new_narrative" in types  # DeFi is new

    def test_acceleration_contains_deltas(self):
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.6, signal_count=15)]
        previous = [_make_cluster(name="AI", theme="AI", composite_score=0.3, signal_count=5)]
        shifts = detect_narrative_shifts(current, previous)
        shift = shifts[0]
        assert "score_delta" in shift
        assert "count_delta" in shift
        assert shift["count_delta"] == 10
        assert "current_score" in shift
        assert "previous_score" in shift

    def test_default_threshold_value(self):
        assert SCORE_DELTA_THRESHOLD == 0.1

    def test_previous_keeps_highest_score_per_theme(self):
        """When multiple previous clusters share a theme, use highest score."""
        current = [_make_cluster(name="AI", theme="AI", composite_score=0.6)]
        previous = [
            _make_cluster(name="AI Low", theme="AI", composite_score=0.2),
            _make_cluster(name="AI High", theme="AI", composite_score=0.45),
        ]
        shifts = detect_narrative_shifts(current, previous)
        assert len(shifts) == 1
        # Delta should be from 0.45 (highest), not 0.2
        assert shifts[0]["type"] == "acceleration"
        assert abs(shifts[0]["previous_score"] - 0.45) < 0.01


class TestSummarizeShifts:
    def test_empty_shifts(self):
        result = summarize_shifts([])
        assert "Nenhuma mudanca" in result

    def test_new_narrative_summary(self):
        shifts = [{"type": "new_narrative", "cluster": "AI Agents", "theme": "AI", "score": 0.5, "signal_count": 10}]
        result = summarize_shifts(shifts)
        assert "Novas narrativas" in result
        assert "AI Agents" in result

    def test_acceleration_summary(self):
        shifts = [{"type": "acceleration", "cluster": "Fintech", "theme": "Fintech", "score_delta": 0.15, "count_delta": 5}]
        result = summarize_shifts(shifts)
        assert "aceleracao" in result
        assert "Fintech" in result
        assert "+0.15" in result

    def test_deceleration_summary(self):
        shifts = [{"type": "deceleration", "cluster": "DeFi", "theme": "DeFi", "score_delta": -0.2}]
        result = summarize_shifts(shifts)
        assert "desaceleracao" in result
        assert "DeFi" in result

    def test_mixed_summary(self):
        shifts = [
            {"type": "new_narrative", "cluster": "A", "theme": "X", "score": 0.5, "signal_count": 3},
            {"type": "acceleration", "cluster": "B", "theme": "Y", "score_delta": 0.2, "count_delta": 10},
            {"type": "deceleration", "cluster": "C", "theme": "Z", "score_delta": -0.15},
        ]
        result = summarize_shifts(shifts)
        assert "Novas narrativas" in result
        assert "aceleracao" in result
        assert "desaceleracao" in result
