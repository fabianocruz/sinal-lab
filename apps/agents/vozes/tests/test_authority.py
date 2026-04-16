"""Tests for the VOZES authority module.

Covers:
- Authority score computation (follower-based, platform weight, engagement)
- Top voices extraction with diversity cap
- Bot detection filtering
- Low authority filtering
"""

from __future__ import annotations

import pytest

from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.vozes.authority import (
    _is_bot,
    compute_authority_score,
    extract_top_voices,
    filter_low_authority,
)


def _make_post(
    text: str = "Test post",
    platform: str = "twitter",
    author_handle: str = "testuser",
    author_followers: int = 0,
    metrics: dict | None = None,
) -> SocialPost:
    """Create a SocialPost for testing."""
    return SocialPost(
        text=text,
        url=f"https://example.com/{author_handle}",
        platform=platform,
        author_handle=author_handle,
        author_display_name=author_handle.replace("_", " ").title(),
        author_followers=author_followers,
        metrics=metrics or {},
    )


def _make_signal(
    text: str = "Test post",
    platform: str = "twitter",
    author_handle: str = "testuser",
    author_followers: int = 0,
    metrics: dict | None = None,
    authority_score: float = 0.5,
    theme: str = "AI",
) -> ProcessedSignal:
    """Create a ProcessedSignal for testing."""
    post = _make_post(
        text=text,
        platform=platform,
        author_handle=author_handle,
        author_followers=author_followers,
        metrics=metrics,
    )
    return ProcessedSignal(
        post=post,
        theme=theme,
        authority_score=authority_score,
    )


# ---------------------------------------------------------------------------
# compute_authority_score
# ---------------------------------------------------------------------------


class TestComputeAuthorityScore:
    """Tests for authority score computation."""

    def test_zero_followers_zero_engagement(self) -> None:
        post = _make_post(author_followers=0, metrics={})
        score = compute_authority_score(post)
        # Should still get platform weight
        assert score > 0.0
        assert score < 0.3  # Only platform weight

    def test_high_followers_increases_score(self) -> None:
        low = _make_post(author_followers=100)
        high = _make_post(author_followers=1_000_000)
        assert compute_authority_score(high) > compute_authority_score(low)

    def test_engagement_increases_score(self) -> None:
        no_engagement = _make_post(metrics={})
        high_engagement = _make_post(metrics={"likes": 500, "replies": 100, "reposts": 50})
        assert compute_authority_score(high_engagement) > compute_authority_score(no_engagement)

    def test_linkedin_platform_weight_highest(self) -> None:
        """LinkedIn should have the highest platform weight."""
        linkedin = _make_post(platform="linkedin")
        twitter = _make_post(platform="twitter")
        reddit = _make_post(platform="reddit")
        assert compute_authority_score(linkedin) > compute_authority_score(reddit)
        assert compute_authority_score(twitter) > compute_authority_score(reddit)

    def test_score_capped_at_one(self) -> None:
        post = _make_post(
            author_followers=100_000_000,
            metrics={"likes": 100_000, "replies": 50_000, "reposts": 30_000},
        )
        score = compute_authority_score(post)
        assert score <= 1.0

    def test_score_always_non_negative(self) -> None:
        post = _make_post(author_followers=0, metrics={})
        score = compute_authority_score(post)
        assert score >= 0.0

    def test_reddit_score_metric(self) -> None:
        """Reddit uses 'score' instead of 'likes'."""
        post = _make_post(platform="reddit", metrics={"score": 500, "comments": 100})
        score = compute_authority_score(post)
        assert score > compute_authority_score(_make_post(platform="reddit"))


# ---------------------------------------------------------------------------
# _is_bot
# ---------------------------------------------------------------------------


class TestIsBot:
    """Tests for bot detection."""

    def test_known_bots_detected(self) -> None:
        assert _is_bot("chatgpt") is True
        assert _is_bot("grok") is True
        assert _is_bot("copilot") is True
        assert _is_bot("perplexity_ai") is True
        assert _is_bot("claudeai") is True

    def test_case_insensitive(self) -> None:
        assert _is_bot("ChatGPT") is True
        assert _is_bot("GROK") is True

    def test_normal_handles_not_bots(self) -> None:
        assert _is_bot("elonmusk") is False
        assert _is_bot("naval") is False
        assert _is_bot("paulg") is False

    def test_bot_pattern_partial_match(self) -> None:
        """Handles containing 'bot' should be detected."""
        assert _is_bot("newsbot2000") is True
        assert _is_bot("tradingbot") is True

    def test_automod_detected(self) -> None:
        assert _is_bot("AutoModerator") is True


# ---------------------------------------------------------------------------
# extract_top_voices
# ---------------------------------------------------------------------------


class TestExtractTopVoices:
    """Tests for top voice extraction with diversity cap."""

    def test_basic_extraction(self) -> None:
        signals = [
            _make_signal(author_handle="alice", authority_score=0.8),
            _make_signal(author_handle="bob", authority_score=0.6),
            _make_signal(author_handle="carol", authority_score=0.4),
        ]
        voices = extract_top_voices(signals, limit=10)
        assert len(voices) == 3
        # Should be sorted by authority (highest first)
        assert voices[0]["handle"] == "alice"

    def test_diversity_cap(self) -> None:
        """With max_per_author=3, prolific authors shouldn't dominate."""
        # Alice has 10 signals but moderate authority
        # Bob has 2 signals but high authority
        signals = []
        for i in range(10):
            signals.append(_make_signal(
                author_handle="alice",
                authority_score=0.3,
            ))
        for i in range(2):
            signals.append(_make_signal(
                author_handle="bob",
                authority_score=0.9,
            ))

        voices = extract_top_voices(signals, limit=5, max_per_author=3)
        # Bob should rank higher despite fewer signals (higher authority)
        assert voices[0]["handle"] == "bob"

    def test_filters_bots(self) -> None:
        signals = [
            _make_signal(author_handle="chatgpt", authority_score=0.9),
            _make_signal(author_handle="alice", authority_score=0.5),
        ]
        voices = extract_top_voices(signals)
        handles = [v["handle"] for v in voices]
        assert "chatgpt" not in handles
        assert "alice" in handles

    def test_limit_respected(self) -> None:
        signals = [
            _make_signal(author_handle=f"user{i}", authority_score=0.5)
            for i in range(20)
        ]
        voices = extract_top_voices(signals, limit=5)
        assert len(voices) == 5

    def test_empty_signals(self) -> None:
        voices = extract_top_voices([])
        assert voices == []

    def test_aggregates_max_authority(self) -> None:
        """When same author has multiple signals, keep the highest authority."""
        signals = [
            _make_signal(author_handle="alice", authority_score=0.3),
            _make_signal(author_handle="alice", authority_score=0.8),
            _make_signal(author_handle="alice", authority_score=0.5),
        ]
        voices = extract_top_voices(signals)
        assert len(voices) == 1
        assert voices[0]["authority"] == 0.8
        assert voices[0]["signal_count"] == 3

    def test_themes_collected(self) -> None:
        signals = [
            _make_signal(author_handle="alice", theme="AI"),
            _make_signal(author_handle="alice", theme="Fintech"),
            _make_signal(author_handle="alice", theme="AI"),  # duplicate theme
        ]
        voices = extract_top_voices(signals)
        assert len(voices) == 1
        assert sorted(voices[0]["themes"]) == ["AI", "Fintech"]

    def test_skips_empty_handles(self) -> None:
        signals = [
            _make_signal(author_handle="", authority_score=0.9),
            _make_signal(author_handle="alice", authority_score=0.5),
        ]
        voices = extract_top_voices(signals)
        handles = [v["handle"] for v in voices]
        assert "" not in handles


# ---------------------------------------------------------------------------
# filter_low_authority
# ---------------------------------------------------------------------------


class TestFilterLowAuthority:
    """Tests for low authority filtering."""

    def test_filters_below_threshold(self) -> None:
        signals = [
            _make_signal(authority_score=0.05),
            _make_signal(authority_score=0.5),
        ]
        result = filter_low_authority(signals, min_score=0.1)
        assert len(result) == 1
        assert result[0].authority_score == 0.5

    def test_keeps_above_threshold(self) -> None:
        signals = [
            _make_signal(authority_score=0.5),
            _make_signal(authority_score=0.8),
        ]
        result = filter_low_authority(signals, min_score=0.1)
        assert len(result) == 2

    def test_at_threshold_kept(self) -> None:
        signals = [_make_signal(authority_score=0.1)]
        result = filter_low_authority(signals, min_score=0.1)
        assert len(result) == 1

    def test_empty_input(self) -> None:
        result = filter_low_authority([])
        assert result == []
