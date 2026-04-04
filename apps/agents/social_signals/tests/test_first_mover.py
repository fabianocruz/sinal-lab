"""Tests for Social Signals first mover detection."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytest

from apps.agents.social_signals.first_mover import (
    EARLY_ADOPTER_WINDOW_HOURS,
    _analyze_cluster_timing,
    _compute_median_timestamp,
    detect_first_movers,
)
from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SocialPost,
)


def _make_signal(
    handle: str = "user1",
    name: str = "User One",
    platform: str = "twitter",
    published_at: Optional[datetime] = None,
    text: str = "some signal text",
    theme: str = "AI",
) -> ProcessedSignal:
    """Create a ProcessedSignal with controlled timing."""
    post = SocialPost(
        text=text,
        url=f"https://example.com/{handle}/{id(published_at)}",
        platform=platform,
        author_handle=handle,
        author_display_name=name,
        published_at=published_at,
    )
    return ProcessedSignal(post=post, theme=theme)


def _make_cluster(
    name: str = "Test Cluster",
    slug: str = "test-cluster",
    signals: Optional[List[ProcessedSignal]] = None,
) -> SignalClusterResult:
    """Create a SignalClusterResult with given signals."""
    return SignalClusterResult(
        name=name,
        slug=slug,
        theme="AI",
        signals=signals or [],
    )


BASE_TIME = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)


class TestComputeMedianTimestamp:
    def test_empty_list(self):
        assert _compute_median_timestamp([]) is None

    def test_single_timestamp(self):
        ts = [BASE_TIME]
        assert _compute_median_timestamp(ts) == BASE_TIME

    def test_odd_count(self):
        ts = [BASE_TIME, BASE_TIME + timedelta(hours=1), BASE_TIME + timedelta(hours=2)]
        assert _compute_median_timestamp(ts) == BASE_TIME + timedelta(hours=1)

    def test_even_count(self):
        ts = [BASE_TIME, BASE_TIME + timedelta(hours=2)]
        result = _compute_median_timestamp(ts)
        expected = BASE_TIME + timedelta(hours=1)
        assert result == expected


class TestDetectFirstMovers:
    def test_empty_clusters(self):
        result = detect_first_movers([], [])
        assert result == {}

    def test_cluster_without_timestamps(self):
        """Signals with no published_at should be excluded."""
        signals = [_make_signal(published_at=None)]
        cluster = _make_cluster(signals=signals)
        result = detect_first_movers(signals, [cluster])
        assert result == {}

    def test_single_signal_cluster(self):
        """Single signal should be identified as first mover with no early adopters."""
        t0 = BASE_TIME
        signals = [_make_signal(handle="pioneer", name="Pioneer", published_at=t0)]
        cluster = _make_cluster(slug="ai-agents", signals=signals)

        result = detect_first_movers(signals, [cluster])

        assert "ai-agents" in result
        data = result["ai-agents"]
        assert data["first_mover"]["handle"] == "pioneer"
        assert data["first_mover"]["name"] == "Pioneer"
        assert data["early_adopters"] == []
        assert data["hours_before_mainstream"] == 0.0

    def test_first_mover_identified_correctly(self):
        """First post chronologically should be the first mover."""
        t0 = BASE_TIME
        t1 = BASE_TIME + timedelta(hours=2)
        t2 = BASE_TIME + timedelta(hours=6)

        signals = [
            _make_signal(handle="late", published_at=t2),
            _make_signal(handle="first", name="First Person", published_at=t0),
            _make_signal(handle="middle", published_at=t1),
        ]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        assert result["test"]["first_mover"]["handle"] == "first"

    def test_early_adopters_within_window(self):
        """Authors posting within 24h of first post should be early adopters."""
        t0 = BASE_TIME
        signals = [
            _make_signal(handle="first", published_at=t0),
            _make_signal(handle="early1", published_at=t0 + timedelta(hours=2)),
            _make_signal(handle="early2", published_at=t0 + timedelta(hours=12)),
            _make_signal(handle="late", published_at=t0 + timedelta(hours=30)),
        ]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        adopters = result["test"]["early_adopters"]
        adopter_handles = [a["handle"] for a in adopters]

        assert "early1" in adopter_handles
        assert "early2" in adopter_handles
        assert "late" not in adopter_handles
        assert "first" not in adopter_handles  # first mover excluded

    def test_early_adopters_capped_at_five(self):
        """Should return at most 5 early adopters."""
        t0 = BASE_TIME
        signals = [_make_signal(handle="first", published_at=t0)]
        for i in range(8):
            signals.append(
                _make_signal(handle=f"adopter{i}", published_at=t0 + timedelta(hours=i + 1))
            )
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        assert len(result["test"]["early_adopters"]) == 5

    def test_hours_before_mainstream(self):
        """Hours between first post and median should be computed correctly."""
        t0 = BASE_TIME
        signals = [
            _make_signal(handle="first", published_at=t0),
            _make_signal(handle="mid", published_at=t0 + timedelta(hours=10)),
            _make_signal(handle="late", published_at=t0 + timedelta(hours=20)),
        ]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        # Median of [0, 10, 20] hours = 10 hours from t0
        assert result["test"]["hours_before_mainstream"] == 10.0

    def test_multiple_clusters(self):
        """Should produce first mover data for each cluster independently."""
        t0 = BASE_TIME
        signals_a = [_make_signal(handle="a_first", published_at=t0)]
        signals_b = [_make_signal(handle="b_first", published_at=t0 + timedelta(hours=5))]

        clusters = [
            _make_cluster(slug="cluster-a", signals=signals_a),
            _make_cluster(slug="cluster-b", signals=signals_b),
        ]

        result = detect_first_movers(signals_a + signals_b, clusters)
        assert "cluster-a" in result
        assert "cluster-b" in result
        assert result["cluster-a"]["first_mover"]["handle"] == "a_first"
        assert result["cluster-b"]["first_mover"]["handle"] == "b_first"

    def test_deduplicates_early_adopters_by_handle(self):
        """Same author posting twice should only appear once in early adopters."""
        t0 = BASE_TIME
        signals = [
            _make_signal(handle="first", published_at=t0),
            _make_signal(handle="repeat", published_at=t0 + timedelta(hours=1)),
            _make_signal(handle="repeat", published_at=t0 + timedelta(hours=2)),
            _make_signal(handle="other", published_at=t0 + timedelta(hours=3)),
        ]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        adopter_handles = [a["handle"] for a in result["test"]["early_adopters"]]
        assert adopter_handles.count("repeat") == 1

    def test_cluster_uses_slug_fallback_to_name(self):
        """When slug is empty, should use name as key."""
        t0 = BASE_TIME
        signals = [_make_signal(handle="user", published_at=t0)]
        cluster = SignalClusterResult(
            name="My Cluster",
            slug="",
            theme="AI",
            signals=signals,
        )

        result = detect_first_movers(signals, [cluster])
        assert "My Cluster" in result

    def test_custom_early_adopter_window(self):
        """Custom window should control early adopter cutoff."""
        t0 = BASE_TIME
        signals = [
            _make_signal(handle="first", published_at=t0),
            _make_signal(handle="within_6h", published_at=t0 + timedelta(hours=5)),
            _make_signal(handle="outside_6h", published_at=t0 + timedelta(hours=8)),
        ]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster], early_adopter_window_hours=6)
        adopter_handles = [a["handle"] for a in result["test"]["early_adopters"]]
        assert "within_6h" in adopter_handles
        assert "outside_6h" not in adopter_handles

    def test_default_window_is_24_hours(self):
        assert EARLY_ADOPTER_WINDOW_HOURS == 24

    def test_first_mover_contains_all_fields(self):
        """First mover dict should have handle, name, platform, posted_at, url."""
        t0 = BASE_TIME
        signals = [_make_signal(handle="user", name="User", platform="bluesky", published_at=t0)]
        cluster = _make_cluster(slug="test", signals=signals)

        result = detect_first_movers(signals, [cluster])
        fm = result["test"]["first_mover"]
        assert set(fm.keys()) == {"handle", "name", "platform", "posted_at", "url"}
        assert fm["platform"] == "bluesky"
        assert fm["posted_at"] == t0.isoformat()
