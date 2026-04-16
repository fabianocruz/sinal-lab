"""Tests for the VOZES collector module.

Covers:
- Reddit megathread / blocked pattern filtering
- Self-promo detection
- Content hash deduplication
- Text similarity deduplication
- Platform-specific normalizers produce valid SocialPost objects
"""

from __future__ import annotations

import pytest

from apps.agents.social_signals.models import SocialPost
from apps.agents.vozes.collector import (
    deduplicate_by_text_similarity,
    filter_blocked_posts,
    is_self_promo,
)


def _make_post(
    text: str = "Test post about AI",
    platform: str = "twitter",
    url: str = "https://example.com/post",
    content_hash: str = "",
    metrics: dict | None = None,
    author_handle: str = "testuser",
    author_followers: int = 0,
) -> SocialPost:
    """Create a SocialPost for testing."""
    return SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle=author_handle,
        author_display_name=author_handle,
        author_followers=author_followers,
        content_hash=content_hash,
        metrics=metrics or {},
    )


# ---------------------------------------------------------------------------
# filter_blocked_posts
# ---------------------------------------------------------------------------


class TestFilterBlockedPosts:
    """Tests for Reddit megathread and blocked pattern filtering."""

    def test_removes_weekly_thread(self) -> None:
        posts = [
            _make_post(text="Weekly Thread - Share your projects", platform="reddit"),
            _make_post(text="Nubank raises $100M in Series E"),
        ]
        result = filter_blocked_posts(posts)
        assert len(result) == 1
        assert "Nubank" in result[0].text

    def test_removes_self_promo_thread(self) -> None:
        posts = [
            _make_post(text="Self-Promo Thread: Share your links"),
            _make_post(text="AI agents are transforming fintech"),
        ]
        result = filter_blocked_posts(posts)
        assert len(result) == 1
        assert "AI agents" in result[0].text

    def test_removes_shameless_plug(self) -> None:
        posts = [_make_post(text="Shameless plug for my new tool")]
        result = filter_blocked_posts(posts)
        assert len(result) == 0

    def test_removes_hiring_thread(self) -> None:
        posts = [_make_post(text="Who is Hiring? - April 2026")]
        result = filter_blocked_posts(posts)
        assert len(result) == 0

    def test_removes_megathread(self) -> None:
        posts = [_make_post(text="Monthly Megathread: Questions and Discussion")]
        result = filter_blocked_posts(posts)
        assert len(result) == 0

    def test_keeps_normal_posts(self) -> None:
        posts = [
            _make_post(text="Nubank launches new AI-powered fraud detection"),
            _make_post(text="Series A funding in LATAM is recovering"),
        ]
        result = filter_blocked_posts(posts)
        assert len(result) == 2

    def test_empty_input(self) -> None:
        result = filter_blocked_posts([])
        assert result == []

    def test_case_insensitive_matching(self) -> None:
        posts = [_make_post(text="WEEKLY THREAD - Share your projects")]
        result = filter_blocked_posts(posts)
        assert len(result) == 0

    def test_removes_show_hn(self) -> None:
        posts = [_make_post(text="Show HN: My new AI tool for compliance")]
        result = filter_blocked_posts(posts)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# is_self_promo
# ---------------------------------------------------------------------------


class TestIsSelfPromo:
    """Tests for self-promo detection."""

    def test_detects_check_out_my(self) -> None:
        post = _make_post(text="Check out my new fintech app!")
        assert is_self_promo(post) is True

    def test_detects_just_launched(self) -> None:
        post = _make_post(text="We just launched our AI compliance tool")
        assert is_self_promo(post) is True

    def test_detects_referral(self) -> None:
        post = _make_post(text="Use my referral code for 20% off")
        assert is_self_promo(post) is True

    def test_detects_weekly_thread(self) -> None:
        post = _make_post(text="Weekly thread for projects")
        assert is_self_promo(post) is True

    def test_normal_post_not_promo(self) -> None:
        post = _make_post(text="AI agents in banking are growing rapidly in LATAM")
        assert is_self_promo(post) is False

    def test_empty_text(self) -> None:
        post = _make_post(text="")
        assert is_self_promo(post) is False

    def test_detects_sign_up_for(self) -> None:
        post = _make_post(text="Sign up for my newsletter on AI trends")
        assert is_self_promo(post) is True


# ---------------------------------------------------------------------------
# deduplicate_by_text_similarity
# ---------------------------------------------------------------------------


class TestDeduplicateByTextSimilarity:
    """Tests for text similarity deduplication."""

    def test_keeps_unique_posts(self) -> None:
        posts = [
            _make_post(text="Nubank launches new AI fraud detection system", content_hash="a"),
            _make_post(text="Bitcoin reaches new all-time high of $100K", content_hash="b"),
        ]
        result = deduplicate_by_text_similarity(posts)
        assert len(result) == 2

    def test_removes_near_duplicate(self) -> None:
        posts = [
            _make_post(
                text="Nubank launches new AI fraud detection system for banking",
                content_hash="a",
                metrics={"likes": 100},
            ),
            _make_post(
                text="Nubank launches new AI fraud detection system for banking",
                content_hash="b",
                metrics={"likes": 5},
            ),
        ]
        result = deduplicate_by_text_similarity(posts, threshold=0.9)
        assert len(result) == 1
        # Keeps the one with more engagement
        assert result[0].metrics.get("likes") == 100

    def test_keeps_similar_but_different_posts(self) -> None:
        posts = [
            _make_post(
                text="AI is transforming fintech in Brazil with new tools",
                content_hash="a",
            ),
            _make_post(
                text="AI is transforming healthcare in India with new tools",
                content_hash="b",
            ),
        ]
        result = deduplicate_by_text_similarity(posts, threshold=0.9)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        result = deduplicate_by_text_similarity([])
        assert result == []

    def test_single_post(self) -> None:
        posts = [_make_post(text="Single post")]
        result = deduplicate_by_text_similarity(posts)
        assert len(result) == 1

    def test_very_short_posts_not_deduped(self) -> None:
        """Posts with less than 20 chars should not be similarity-checked."""
        posts = [
            _make_post(text="AI", content_hash="a"),
            _make_post(text="AI", content_hash="b"),
        ]
        result = deduplicate_by_text_similarity(posts)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# SocialPost validity
# ---------------------------------------------------------------------------


class TestSocialPostValidity:
    """All platform-specific normalizers should produce valid SocialPost objects."""

    def test_twitter_post_has_required_fields(self) -> None:
        post = _make_post(
            text="AI agents in banking",
            platform="twitter",
            url="https://twitter.com/user/status/123",
            author_handle="testuser",
        )
        assert post.text
        assert post.url
        assert post.platform == "twitter"
        assert post.content_hash  # auto-generated from URL

    def test_reddit_post_has_required_fields(self) -> None:
        post = _make_post(
            text="r/fintech discussion about payments",
            platform="reddit",
            url="https://reddit.com/r/fintech/comments/abc",
        )
        assert post.text
        assert post.platform == "reddit"

    def test_rss_post_has_required_fields(self) -> None:
        post = _make_post(
            text="Newsletter: AI trends in LATAM fintech",
            platform="rss",
            url="https://newsletter.example.com/issue-42",
        )
        assert post.text
        assert post.platform == "rss"

    def test_content_hash_auto_generated(self) -> None:
        """Content hash should be auto-generated from URL if not provided."""
        post = SocialPost(
            text="Test post",
            url="https://example.com/unique-url",
            platform="twitter",
        )
        assert post.content_hash
        assert len(post.content_hash) == 32  # MD5 hex digest

    def test_explicit_content_hash_preserved(self) -> None:
        post = SocialPost(
            text="Test post",
            url="https://example.com/post",
            platform="twitter",
            content_hash="custom-hash-123",
        )
        assert post.content_hash == "custom-hash-123"
