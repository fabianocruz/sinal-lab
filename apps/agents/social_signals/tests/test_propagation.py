"""Tests for cross-platform propagation tracking."""

from typing import Optional

import pytest

from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.social_signals.propagation import (
    compute_propagation_score,
    enrich_signals_with_propagation,
    track_cross_platform,
)


def _make_signal(
    text: str = "test",
    platform: str = "twitter",
    url: str = "https://twitter.com/1",
    external_url: Optional[str] = None,
    content_hash: str = "",
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=url,
        platform=platform,
        external_url=external_url,
        content_hash=content_hash or "",
    )
    return ProcessedSignal(post=post, theme="AI")


class TestComputePropagationScore:
    def test_zero_platforms(self):
        assert compute_propagation_score([]) == 0.0

    def test_one_platform(self):
        assert compute_propagation_score(["twitter"]) == 0.2

    def test_two_platforms(self):
        assert compute_propagation_score(["twitter", "reddit"]) == 0.5

    def test_three_platforms(self):
        assert compute_propagation_score(["twitter", "reddit", "bluesky"]) == 0.75

    def test_four_or_more_platforms(self):
        assert compute_propagation_score(["twitter", "reddit", "bluesky", "rss"]) == 1.0

    def test_deduplicates_platforms(self):
        assert compute_propagation_score(["twitter", "twitter", "twitter"]) == 0.2


class TestTrackCrossPlatform:
    def test_empty_signals(self):
        result = track_cross_platform([])
        assert result == {}

    def test_single_platform_not_included(self):
        signals = [
            _make_signal(platform="twitter", external_url="https://example.com/article"),
            _make_signal(platform="twitter", external_url="https://example.com/article"),
        ]
        result = track_cross_platform(signals)
        assert len(result) == 0

    def test_same_url_two_platforms(self):
        signals = [
            _make_signal(
                platform="twitter",
                external_url="https://example.com/article",
                url="https://twitter.com/1",
            ),
            _make_signal(
                platform="reddit",
                external_url="https://example.com/article",
                url="https://reddit.com/1",
            ),
        ]
        result = track_cross_platform(signals)
        assert "https://example.com/article" in result
        assert set(result["https://example.com/article"]) == {"reddit", "twitter"}

    def test_same_hash_two_platforms(self):
        signals = [
            _make_signal(platform="twitter", content_hash="abc123"),
            _make_signal(platform="bluesky", content_hash="abc123"),
        ]
        result = track_cross_platform(signals)
        assert len(result) >= 1  # Either by hash or URL

    def test_multiple_groups(self):
        signals = [
            _make_signal(platform="twitter", external_url="https://a.com", url="https://t.co/1", content_hash="h1"),
            _make_signal(platform="reddit", external_url="https://a.com", url="https://reddit.com/1", content_hash="h2"),
            _make_signal(platform="twitter", external_url="https://b.com", url="https://t.co/2", content_hash="h3"),
            _make_signal(platform="bluesky", external_url="https://b.com", url="https://bsky.app/1", content_hash="h4"),
        ]
        result = track_cross_platform(signals)
        # At least 2 URL-based groups (may also have hash-based)
        url_groups = [k for k in result if k.startswith("https://")]
        assert len(url_groups) == 2

    def test_no_external_url_different_hashes(self):
        signals = [
            _make_signal(platform="twitter", external_url=None, url="https://t.co/1", content_hash="unique_a"),
            _make_signal(platform="reddit", external_url=None, url="https://reddit.com/1", content_hash="unique_b"),
        ]
        result = track_cross_platform(signals)
        # Different content hashes and no shared external_url: no cross-platform groups
        assert len(result) == 0


class TestEnrichSignalsWithPropagation:
    def test_empty_signals(self):
        result = enrich_signals_with_propagation([])
        assert result == {}

    def test_single_platform_no_enrichment(self):
        signals = [
            _make_signal(platform="twitter", external_url="https://a.com"),
        ]
        result = enrich_signals_with_propagation(signals)
        assert len(result) == 0

    def test_cross_platform_enriched(self):
        signals = [
            _make_signal(
                platform="twitter",
                external_url="https://article.com",
                url="https://twitter.com/1",
                content_hash="hash_a",
            ),
            _make_signal(
                platform="reddit",
                external_url="https://article.com",
                url="https://reddit.com/1",
                content_hash="hash_b",
            ),
        ]
        result = enrich_signals_with_propagation(signals)
        # Both signals should get enriched via shared external_url
        assert "hash_a" in result
        assert "hash_b" in result
        assert result["hash_a"] == 0.5  # 2 platforms
        assert result["hash_b"] == 0.5

    def test_three_platforms_higher_score(self):
        signals = [
            _make_signal(
                platform="twitter",
                external_url="https://article.com",
                url="https://twitter.com/1",
                content_hash="h1",
            ),
            _make_signal(
                platform="reddit",
                external_url="https://article.com",
                url="https://reddit.com/1",
                content_hash="h2",
            ),
            _make_signal(
                platform="bluesky",
                external_url="https://article.com",
                url="https://bsky.app/1",
                content_hash="h3",
            ),
        ]
        result = enrich_signals_with_propagation(signals)
        assert result.get("h1", 0) == 0.75
        assert result.get("h2", 0) == 0.75
        assert result.get("h3", 0) == 0.75

    def test_hash_based_cross_platform(self):
        """Signals sharing content_hash across platforms get propagation score."""
        signals = [
            _make_signal(
                platform="twitter",
                url="https://twitter.com/1",
                content_hash="same_hash",
            ),
            _make_signal(
                platform="reddit",
                url="https://reddit.com/1",
                content_hash="same_hash",
            ),
        ]
        result = enrich_signals_with_propagation(signals)
        assert result.get("same_hash", 0) == 0.5
