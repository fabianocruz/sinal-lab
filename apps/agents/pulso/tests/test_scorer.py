"""Tests for the PULSO scorer module.

Covers velocity defaults, top posts platform field, top voices author cap,
composite score weights, and narrative stage distribution.
"""

from __future__ import annotations

import pytest

from apps.agents.pulso.config import DIMENSION_WEIGHTS
from apps.agents.pulso.models import ProcessedSignal, SignalDimensions, SocialPost
from apps.agents.pulso.scorer import (
    _compute_authority_concentration,
    _compute_commercial_signals,
    _compute_cross_platform,
    _compute_narrative_maturity,
    _compute_new_entrants,
    _compute_sentiment_shift,
    _compute_velocity,
    _compute_volume,
    assign_narrative_stages_by_percentile,
    classify_signal_type,
    compute_cluster_dimensions,
    determine_narrative_stage,
    extract_top_posts,
    extract_top_voices,
    strip_html,
)
from apps.agents.pulso.models import SignalClusterResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    text: str = "Test post about AI technology",
    platform: str = "twitter",
    author: str = "user1",
    authority: float = 0.5,
    sentiment: float = 0.0,
    is_commercial: bool = False,
    followers: int = 1000,
    metrics: dict | None = None,
    content_hash: str = "",
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=f"https://example.com/{content_hash or author}",
        platform=platform,
        author_handle=author,
        author_display_name=author.title(),
        author_followers=followers,
        metrics=metrics or {},
        content_hash=content_hash or "",
    )
    return ProcessedSignal(
        post=post,
        theme="AI",
        authority_score=authority,
        sentiment=sentiment,
        is_commercial=is_commercial,
    )


# ---------------------------------------------------------------------------
# Velocity defaults
# ---------------------------------------------------------------------------


class TestVelocityDefault:
    def test_no_history_returns_0_3(self) -> None:
        """Velocity should default to 0.3 (not 0.5) when no previous data."""
        velocity = _compute_velocity(current_count=10, previous_count=0)
        assert velocity == 0.3

    def test_no_signals_returns_0(self) -> None:
        velocity = _compute_velocity(current_count=0, previous_count=0)
        assert velocity == 0.0

    def test_doubling_above_0_3(self) -> None:
        velocity = _compute_velocity(current_count=20, previous_count=10)
        assert velocity > 0.3

    def test_decline_below_0_3(self) -> None:
        velocity = _compute_velocity(current_count=5, previous_count=20)
        assert velocity < 0.3


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


class TestVolume:
    def test_zero_returns_zero(self) -> None:
        assert _compute_volume(0) == 0.0

    def test_ten_around_third(self) -> None:
        vol = _compute_volume(10)
        assert 0.3 <= vol <= 0.4

    def test_thousand_near_one(self) -> None:
        vol = _compute_volume(1000)
        assert vol >= 0.95


# ---------------------------------------------------------------------------
# Authority concentration
# ---------------------------------------------------------------------------


class TestAuthorityConcentration:
    def test_all_high_authority(self) -> None:
        signals = [_make_signal(authority=0.8) for _ in range(10)]
        assert _compute_authority_concentration(signals) == 1.0

    def test_all_low_authority(self) -> None:
        signals = [_make_signal(authority=0.2) for _ in range(10)]
        assert _compute_authority_concentration(signals) == 0.0

    def test_empty(self) -> None:
        assert _compute_authority_concentration([]) == 0.0


# ---------------------------------------------------------------------------
# Cross-platform propagation
# ---------------------------------------------------------------------------


class TestCrossPlatform:
    def test_single_platform(self) -> None:
        signals = [_make_signal(platform="twitter") for _ in range(5)]
        assert _compute_cross_platform(signals) == 0.2

    def test_two_platforms(self) -> None:
        signals = [
            _make_signal(platform="twitter"),
            _make_signal(platform="reddit"),
        ]
        assert _compute_cross_platform(signals) == 0.5

    def test_four_platforms(self) -> None:
        signals = [
            _make_signal(platform="twitter"),
            _make_signal(platform="reddit"),
            _make_signal(platform="bluesky"),
            _make_signal(platform="rss"),
        ]
        assert _compute_cross_platform(signals) == 1.0


# ---------------------------------------------------------------------------
# Sentiment shift
# ---------------------------------------------------------------------------


class TestSentimentShift:
    def test_no_shift(self) -> None:
        signals = [_make_signal(sentiment=0.5) for _ in range(5)]
        shift = _compute_sentiment_shift(signals, previous_sentiment=0.5)
        assert shift == 0.0

    def test_large_shift(self) -> None:
        signals = [_make_signal(sentiment=0.8) for _ in range(5)]
        shift = _compute_sentiment_shift(signals, previous_sentiment=0.0)
        assert shift > 0.5


# ---------------------------------------------------------------------------
# New entrants
# ---------------------------------------------------------------------------


class TestNewEntrants:
    def test_all_new(self) -> None:
        signals = [_make_signal(author=f"new_{i}") for i in range(5)]
        known = {"old_author"}
        score = _compute_new_entrants(signals, known)
        assert score == 1.0

    def test_all_known(self) -> None:
        signals = [_make_signal(author=f"known_{i}") for i in range(3)]
        known = {f"known_{i}" for i in range(3)}
        score = _compute_new_entrants(signals, known)
        assert score == 0.0

    def test_no_history_neutral(self) -> None:
        signals = [_make_signal(author="user1")]
        score = _compute_new_entrants(signals, set())
        assert score == 0.5


# ---------------------------------------------------------------------------
# Narrative maturity
# ---------------------------------------------------------------------------


class TestNarrativeMaturity:
    def test_short_text_low(self) -> None:
        signals = [_make_signal(text="Short post")]
        score = _compute_narrative_maturity(signals)
        assert score < 0.1

    def test_long_text_high(self) -> None:
        signals = [_make_signal(text="x" * 600)]
        score = _compute_narrative_maturity(signals)
        assert score >= 1.0


# ---------------------------------------------------------------------------
# Commercial signals
# ---------------------------------------------------------------------------


class TestCommercialSignals:
    def test_no_commercial(self) -> None:
        signals = [_make_signal(is_commercial=False) for _ in range(5)]
        assert _compute_commercial_signals(signals) == 0.0

    def test_all_commercial(self) -> None:
        signals = [_make_signal(is_commercial=True) for _ in range(5)]
        score = _compute_commercial_signals(signals)
        assert score > 0.5


# ---------------------------------------------------------------------------
# Composite score uses PULSO weights
# ---------------------------------------------------------------------------


class TestCompositeScore:
    def test_uses_pulso_weights(self) -> None:
        """Verify composite_score uses PULSO dimension weights by default."""
        dims = SignalDimensions(
            volume=1.0,
            velocity=1.0,
            authority_concentration=1.0,
            cross_platform_propagation=1.0,
            sentiment_shift=1.0,
            new_entrants=1.0,
            narrative_maturity=1.0,
            commercial_signals=1.0,
        )
        score = dims.composite_score()
        # All dimensions at 1.0, sum of all weights should be 1.0
        expected = sum(DIMENSION_WEIGHTS.values())
        assert abs(score - expected) < 0.01

    def test_weights_sum_to_one(self) -> None:
        """PULSO weights must sum to 1.0."""
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_velocity_weight_reduced(self) -> None:
        """Velocity weight should be 0.15 (not 0.20 like social_signals)."""
        assert DIMENSION_WEIGHTS["velocity"] == 0.15

    def test_authority_weight_increased(self) -> None:
        """Authority weight should be 0.20 (not 0.15 like social_signals)."""
        assert DIMENSION_WEIGHTS["authority_concentration"] == 0.20

    def test_commercial_weight_reduced(self) -> None:
        """Commercial weight should be 0.05 (not 0.10 like social_signals)."""
        assert DIMENSION_WEIGHTS["commercial_signals"] == 0.05


# ---------------------------------------------------------------------------
# Top posts — platform field
# ---------------------------------------------------------------------------


class TestExtractTopPosts:
    def test_includes_platform_field(self) -> None:
        """Every top post must include a 'platform' field."""
        signals = [
            _make_signal(
                text="A" * 100,
                platform="twitter",
                metrics={"likes": 50},
                content_hash=f"post_{i}",
                author=f"author_{i}",
            )
            for i in range(5)
        ]
        posts = extract_top_posts(signals, limit=5)
        assert len(posts) > 0
        for post in posts:
            assert "platform" in post
            assert post["platform"] == "twitter"

    def test_max_3_per_author(self) -> None:
        """No author should have more than 3 posts in top posts."""
        signals = [
            _make_signal(
                text="A" * 100,
                platform="twitter",
                author="prolific_author",
                metrics={"likes": 100 - i},
                content_hash=f"prolific_{i}",
            )
            for i in range(10)
        ]
        posts = extract_top_posts(signals, limit=10)
        author_counts: dict[str, int] = {}
        for p in posts:
            author = p.get("author", "")
            author_counts[author] = author_counts.get(author, 0) + 1

        for author, count in author_counts.items():
            assert count <= 3, f"Author {author} has {count} posts (max 3)"

    def test_skips_bots(self) -> None:
        signals = [
            _make_signal(
                text="A" * 100,
                author="chatgpt",
                metrics={"likes": 1000},
                content_hash="bot_post",
            ),
        ]
        posts = extract_top_posts(signals, limit=5)
        assert len(posts) == 0

    def test_skips_short_text(self) -> None:
        signals = [
            _make_signal(
                text="Short",
                metrics={},
                content_hash="short_post",
            ),
        ]
        posts = extract_top_posts(signals, limit=5)
        assert len(posts) == 0

    def test_text_truncated_to_300(self) -> None:
        signals = [
            _make_signal(
                text="A" * 500,
                metrics={"likes": 10},
                content_hash="long_post",
            ),
        ]
        posts = extract_top_posts(signals, limit=1)
        assert len(posts) == 1
        assert len(posts[0]["text"]) <= 300


# ---------------------------------------------------------------------------
# Top voices — author cap
# ---------------------------------------------------------------------------


class TestExtractTopVoices:
    def test_dedup_by_handle(self) -> None:
        signals = [
            _make_signal(author="alice", authority=0.9, content_hash=f"alice_{i}")
            for i in range(5)
        ]
        voices = extract_top_voices(signals, limit=10)
        # Should be 1 entry for alice (deduped by handle)
        assert len(voices) == 1
        assert voices[0]["handle"] == "alice"
        assert voices[0]["signal_count"] == 5

    def test_skips_bots(self) -> None:
        signals = [
            _make_signal(author="chatgpt", authority=0.9),
        ]
        voices = extract_top_voices(signals, limit=5)
        assert len(voices) == 0


# ---------------------------------------------------------------------------
# Compute cluster dimensions
# ---------------------------------------------------------------------------


class TestComputeClusterDimensions:
    def test_returns_all_dimensions(self) -> None:
        signals = [_make_signal() for _ in range(10)]
        dims = compute_cluster_dimensions(signals)
        assert dims.volume > 0
        assert 0 <= dims.velocity <= 1
        assert 0 <= dims.authority_concentration <= 1

    def test_empty_signals(self) -> None:
        dims = compute_cluster_dimensions([])
        assert dims.volume == 0.0
        assert dims.velocity == 0.0


# ---------------------------------------------------------------------------
# Narrative stages
# ---------------------------------------------------------------------------


class TestDetermineNarrativeStage:
    def test_no_history_high_score_accelerating(self) -> None:
        dims = SignalDimensions(
            volume=0.8,
            velocity=0.3,
            authority_concentration=0.7,
            cross_platform_propagation=0.8,
        )
        stage = determine_narrative_stage(dims, has_historical_data=False)
        assert stage == "accelerating"

    def test_no_history_low_score_declining(self) -> None:
        dims = SignalDimensions(
            volume=0.05,
            velocity=0.3,
        )
        stage = determine_narrative_stage(dims, has_historical_data=False)
        assert stage in ("declining", "weak_signal")

    def test_with_history_high_velocity(self) -> None:
        # weeks_active=1 (default) triggers "emerging" path first.
        # With weeks_active > 2 and high velocity, it returns "accelerating".
        dims = SignalDimensions(velocity=0.7, volume=0.5)
        stage = determine_narrative_stage(dims, weeks_active=3, has_historical_data=True)
        assert stage == "accelerating"

    def test_with_history_peaking(self) -> None:
        dims = SignalDimensions(velocity=0.1, volume=0.8)
        stage = determine_narrative_stage(dims, has_historical_data=True)
        assert stage == "peaking"


class TestAssignNarrativeStagesByPercentile:
    def test_distributes_stages(self) -> None:
        """With 10 clusters, should get a mix of stages."""
        clusters = []
        for i in range(10):
            c = SignalClusterResult(
                name=f"Cluster {i}",
                slug=f"cluster-{i}",
                signals=[_make_signal(content_hash=f"c{i}_s{j}") for j in range(5 + i)],
                dimensions=SignalDimensions(
                    volume=0.1 * (i + 1),
                    authority_concentration=0.1 * (i + 1),
                    cross_platform_propagation=0.2,
                ),
            )
            clusters.append(c)

        assign_narrative_stages_by_percentile(clusters, has_historical_data=False)

        stages = [c.narrative_stage for c in clusters]
        unique_stages = set(stages)
        # Should have at least 2 different stages
        assert len(unique_stages) >= 2, f"Only got stages: {unique_stages}"

    def test_no_op_with_historical_data(self) -> None:
        clusters = [
            SignalClusterResult(
                name="Test",
                slug="test",
                signals=[_make_signal()],
                dimensions=SignalDimensions(volume=0.5),
                narrative_stage="emerging",
            )
        ]
        assign_narrative_stages_by_percentile(clusters, has_historical_data=True)
        assert clusters[0].narrative_stage == "emerging"  # Unchanged


# ---------------------------------------------------------------------------
# Classify signal type
# ---------------------------------------------------------------------------


class TestClassifySignalType:
    def test_trend(self) -> None:
        # Needs volume > 0.6 AND composite > 0.5. With PULSO weights,
        # high scores across all dimensions ensure composite exceeds 0.5.
        dims = SignalDimensions(
            volume=0.8, velocity=0.8, authority_concentration=0.8,
            cross_platform_propagation=0.8, sentiment_shift=0.5,
            new_entrants=0.5, narrative_maturity=0.5, commercial_signals=0.5,
        )
        assert classify_signal_type(dims) == "trend"

    def test_emerging(self) -> None:
        dims = SignalDimensions(volume=0.3, velocity=0.7, authority_concentration=0.6)
        assert classify_signal_type(dims) == "emerging_signal"

    def test_weak(self) -> None:
        dims = SignalDimensions(volume=0.1, velocity=0.2)
        assert classify_signal_type(dims) == "weak_signal"


# ---------------------------------------------------------------------------
# Strip HTML
# ---------------------------------------------------------------------------


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_decodes_entities(self) -> None:
        assert strip_html("A &amp; B") == "A & B"
