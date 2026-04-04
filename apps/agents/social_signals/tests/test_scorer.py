"""Tests for social signals scorer — dimension computation with controlled data."""

import pytest

from apps.agents.social_signals.models import (
    EntityMention,
    ProcessedSignal,
    SignalDimensions,
    SocialPost,
)
from apps.agents.social_signals.scorer import (
    _compute_authority_concentration,
    _compute_commercial_signals,
    _compute_cross_platform,
    _compute_narrative_maturity,
    _compute_new_entrants,
    _compute_sentiment_shift,
    _compute_velocity,
    _compute_volume,
    classify_signal_type,
    compute_cluster_dimensions,
    determine_narrative_stage,
    extract_top_posts,
    extract_top_voices,
)


def _make_signal(
    text: str = "test",
    platform: str = "twitter",
    author_handle: str = "user1",
    author_followers: int = 1000,
    authority_score: float = 0.5,
    sentiment: float = 0.0,
    is_commercial: bool = False,
    likes: int = 0,
    replies: int = 0,
    reposts: int = 0,
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=f"https://twitter.com/{author_handle}/1",
        platform=platform,
        author_handle=author_handle,
        author_display_name=author_handle,
        author_followers=author_followers,
        metrics={"likes": likes, "replies": replies, "reposts": reposts},
    )
    return ProcessedSignal(
        post=post,
        theme="AI",
        authority_score=authority_score,
        sentiment=sentiment,
        is_commercial=is_commercial,
    )


class TestComputeVolume:
    def test_zero_posts(self):
        assert _compute_volume(0) == 0.0

    def test_ten_posts(self):
        score = _compute_volume(10)
        assert 0.3 < score < 0.4

    def test_hundred_posts(self):
        score = _compute_volume(100)
        assert 0.6 < score < 0.7

    def test_thousand_posts_caps_at_one(self):
        score = _compute_volume(1000)
        assert score == 1.0

    def test_negative_posts(self):
        assert _compute_volume(-5) == 0.0


class TestComputeVelocity:
    def test_no_previous_with_current(self):
        assert _compute_velocity(10, 0) == 0.5

    def test_no_previous_no_current(self):
        assert _compute_velocity(0, 0) == 0.0

    def test_doubling(self):
        score = _compute_velocity(20, 10)
        assert score > 0.3  # Growth

    def test_decline(self):
        score = _compute_velocity(5, 10)
        assert score < 0.3  # Decline

    def test_ten_x_growth(self):
        score = _compute_velocity(100, 10)
        assert score >= 0.9


class TestComputeAuthority:
    def test_no_signals(self):
        assert _compute_authority_concentration([]) == 0.0

    def test_all_high_authority(self):
        signals = [_make_signal(authority_score=0.8) for _ in range(5)]
        assert _compute_authority_concentration(signals) == 1.0

    def test_all_low_authority(self):
        signals = [_make_signal(authority_score=0.2) for _ in range(5)]
        assert _compute_authority_concentration(signals) == 0.0

    def test_mixed_authority(self):
        signals = [
            _make_signal(authority_score=0.8),
            _make_signal(authority_score=0.3),
            _make_signal(authority_score=0.7),
            _make_signal(authority_score=0.1),
        ]
        assert _compute_authority_concentration(signals) == 0.5


class TestComputeCrossPlatform:
    def test_single_platform(self):
        signals = [_make_signal(platform="twitter") for _ in range(3)]
        assert _compute_cross_platform(signals) == 0.2

    def test_two_platforms(self):
        signals = [
            _make_signal(platform="twitter"),
            _make_signal(platform="reddit"),
        ]
        assert _compute_cross_platform(signals) == 0.5

    def test_three_platforms(self):
        signals = [
            _make_signal(platform="twitter"),
            _make_signal(platform="reddit"),
            _make_signal(platform="bluesky"),
        ]
        assert _compute_cross_platform(signals) == 0.75

    def test_four_platforms(self):
        signals = [
            _make_signal(platform="twitter"),
            _make_signal(platform="reddit"),
            _make_signal(platform="bluesky"),
            _make_signal(platform="rss"),
        ]
        assert _compute_cross_platform(signals) == 1.0


class TestComputeSentimentShift:
    def test_no_signals(self):
        assert _compute_sentiment_shift([], 0.0) == 0.0

    def test_no_shift(self):
        signals = [_make_signal(sentiment=0.5) for _ in range(3)]
        assert _compute_sentiment_shift(signals, 0.5) == 0.0

    def test_large_positive_shift(self):
        signals = [_make_signal(sentiment=0.8) for _ in range(3)]
        score = _compute_sentiment_shift(signals, 0.0)
        assert score > 0.5

    def test_capped_at_one(self):
        signals = [_make_signal(sentiment=1.0) for _ in range(3)]
        score = _compute_sentiment_shift(signals, -1.0)
        assert score <= 1.0


class TestComputeNewEntrants:
    def test_no_signals(self):
        assert _compute_new_entrants([], set()) == 0.0

    def test_no_known_authors(self):
        signals = [_make_signal(author_handle="new_user")]
        assert _compute_new_entrants(signals, set()) == 0.5  # Neutral

    def test_all_new_authors(self):
        signals = [_make_signal(author_handle=f"user_{i}") for i in range(5)]
        known = {"old_user_1", "old_user_2"}
        assert _compute_new_entrants(signals, known) == 1.0

    def test_all_known_authors(self):
        signals = [_make_signal(author_handle="known_user")]
        known = {"known_user"}
        assert _compute_new_entrants(signals, known) == 0.0


class TestComputeNarrativeMaturity:
    def test_no_signals(self):
        assert _compute_narrative_maturity([]) == 0.0

    def test_short_posts(self):
        signals = [_make_signal(text="Short") for _ in range(3)]
        score = _compute_narrative_maturity(signals)
        assert score < 0.1

    def test_long_analytical_posts(self):
        signals = [_make_signal(text="x" * 600) for _ in range(3)]
        score = _compute_narrative_maturity(signals)
        assert score >= 1.0


class TestComputeCommercialSignals:
    def test_no_signals(self):
        assert _compute_commercial_signals([]) == 0.0

    def test_all_commercial(self):
        signals = [_make_signal(is_commercial=True) for _ in range(5)]
        score = _compute_commercial_signals(signals)
        assert score > 0.5

    def test_no_commercial(self):
        signals = [_make_signal(is_commercial=False) for _ in range(5)]
        assert _compute_commercial_signals(signals) == 0.0


class TestComputeClusterDimensions:
    def test_empty_signals(self):
        dims = compute_cluster_dimensions([])
        assert dims.volume == 0.0
        assert dims.velocity == 0.0

    def test_full_computation(self):
        signals = [
            _make_signal(platform="twitter", authority_score=0.8, sentiment=0.5),
            _make_signal(platform="reddit", authority_score=0.6, sentiment=0.3),
        ]
        dims = compute_cluster_dimensions(signals, previous_count=5)
        assert dims.volume > 0
        assert dims.velocity > 0
        assert dims.cross_platform_propagation == 0.5  # 2 platforms


class TestClassifySignalType:
    def test_trend(self):
        dims = SignalDimensions(
            volume=0.8, velocity=0.7, authority_concentration=0.6,
            cross_platform_propagation=0.5, sentiment_shift=0.4,
            new_entrants=0.3, narrative_maturity=0.5, commercial_signals=0.3,
        )
        assert classify_signal_type(dims) == "trend"

    def test_emerging_signal(self):
        dims = SignalDimensions(volume=0.2, velocity=0.6, authority_concentration=0.5)
        assert classify_signal_type(dims) == "emerging_signal"

    def test_weak_signal(self):
        dims = SignalDimensions(volume=0.1, velocity=0.1)
        assert classify_signal_type(dims) == "weak_signal"


class TestDetermineNarrativeStage:
    def test_emerging(self):
        dims = SignalDimensions(velocity=0.5, volume=0.2)
        assert determine_narrative_stage(dims, weeks_active=1) == "emerging"

    def test_accelerating(self):
        dims = SignalDimensions(velocity=0.6, volume=0.5)
        assert determine_narrative_stage(dims, weeks_active=5) == "accelerating"

    def test_peaking(self):
        dims = SignalDimensions(velocity=0.1, volume=0.8)
        assert determine_narrative_stage(dims, weeks_active=8) == "peaking"

    # --- First-run (no historical data) score-based fallback ---

    def test_first_run_high_score_is_accelerating(self):
        """On first run, clusters with composite > 0.4 should be accelerating."""
        dims = SignalDimensions(
            volume=0.5, velocity=0.5, authority_concentration=0.6,
            cross_platform_propagation=0.5, sentiment_shift=0.3,
            new_entrants=0.5, narrative_maturity=0.4, commercial_signals=0.3,
        )
        result = determine_narrative_stage(dims, weeks_active=1, has_historical_data=False)
        assert result == "accelerating"

    def test_first_run_medium_score_is_emerging(self):
        """On first run, clusters with composite 0.3-0.4 should be emerging."""
        dims = SignalDimensions(
            volume=0.3, velocity=0.5, authority_concentration=0.4,
            cross_platform_propagation=0.3, sentiment_shift=0.2,
            new_entrants=0.5, narrative_maturity=0.3, commercial_signals=0.2,
        )
        result = determine_narrative_stage(dims, weeks_active=1, has_historical_data=False)
        assert result == "emerging"

    def test_first_run_low_score_is_weak_signal(self):
        """On first run, clusters with composite 0.2-0.3 should be weak_signal."""
        dims = SignalDimensions(
            volume=0.1, velocity=0.5, authority_concentration=0.1,
            cross_platform_propagation=0.2, sentiment_shift=0.0,
            new_entrants=0.5, narrative_maturity=0.1, commercial_signals=0.0,
        )
        result = determine_narrative_stage(dims, weeks_active=1, has_historical_data=False)
        assert result == "weak_signal"

    def test_first_run_very_low_score_is_declining(self):
        """On first run, clusters with composite <= 0.2 should be declining."""
        dims = SignalDimensions(
            volume=0.05, velocity=0.5, authority_concentration=0.0,
            cross_platform_propagation=0.2, sentiment_shift=0.0,
            new_entrants=0.0, narrative_maturity=0.0, commercial_signals=0.0,
        )
        result = determine_narrative_stage(dims, weeks_active=1, has_historical_data=False)
        assert result == "declining"

    def test_with_historical_data_uses_velocity_logic(self):
        """When has_historical_data=True, uses velocity-based logic (default)."""
        dims = SignalDimensions(velocity=0.6, volume=0.5)
        # has_historical_data=True is default, should use velocity logic
        assert determine_narrative_stage(dims, weeks_active=5, has_historical_data=True) == "accelerating"


class TestExtractTopVoices:
    def test_empty(self):
        assert extract_top_voices([]) == []

    def test_returns_top_by_authority(self):
        signals = [
            _make_signal(author_handle="low", authority_score=0.1),
            _make_signal(author_handle="high", authority_score=0.9),
            _make_signal(author_handle="mid", authority_score=0.5),
        ]
        voices = extract_top_voices(signals, limit=2)
        assert len(voices) == 2
        assert voices[0]["handle"] == "high"


class TestExtractTopPosts:
    def test_empty(self):
        assert extract_top_posts([]) == []

    def test_ranks_by_engagement(self):
        signals = [
            _make_signal(likes=10, reposts=0, authority_score=0.1),
            _make_signal(likes=100, reposts=50, authority_score=0.5),
        ]
        posts = extract_top_posts(signals, limit=1)
        assert len(posts) == 1
        # Second signal has higher engagement
        assert posts[0]["platform"] == "twitter"
