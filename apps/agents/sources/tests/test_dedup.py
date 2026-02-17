"""Tests for shared deduplication utilities.

Tests compute_content_hash, compute_composite_hash, and deduplicate_by_hash
functions that replace 5 copies of inline dedup code across collectors.
"""

from dataclasses import dataclass

import pytest

from apps.agents.sources.dedup import (
    compute_composite_hash,
    compute_content_hash,
    deduplicate_by_hash,
)


class TestComputeContentHash:
    """Test URL-based content hashing."""

    def test_deterministic(self) -> None:
        hash1 = compute_content_hash("https://example.com/article")
        hash2 = compute_content_hash("https://example.com/article")
        assert hash1 == hash2

    def test_different_urls_different_hashes(self) -> None:
        hash1 = compute_content_hash("https://example.com/1")
        hash2 = compute_content_hash("https://example.com/2")
        assert hash1 != hash2

    def test_returns_md5_hex_digest(self) -> None:
        result = compute_content_hash("https://example.com")
        assert len(result) == 32  # MD5 hex = 32 chars
        assert all(c in "0123456789abcdef" for c in result)


class TestComputeCompositeHash:
    """Test composite hashing from multiple parts."""

    def test_deterministic(self) -> None:
        hash1 = compute_composite_hash("Nubank", "series_a", "https://example.com")
        hash2 = compute_composite_hash("Nubank", "series_a", "https://example.com")
        assert hash1 == hash2

    def test_different_parts_different_hashes(self) -> None:
        hash1 = compute_composite_hash("Nubank", "series_a")
        hash2 = compute_composite_hash("Nubank", "series_b")
        assert hash1 != hash2

    def test_joins_with_separator(self) -> None:
        """Different orderings produce different hashes."""
        hash1 = compute_composite_hash("a", "b")
        hash2 = compute_composite_hash("b", "a")
        assert hash1 != hash2

    def test_single_part(self) -> None:
        result = compute_composite_hash("single")
        assert len(result) == 32

    def test_returns_md5_hex_digest(self) -> None:
        result = compute_composite_hash("a", "b", "c")
        assert len(result) == 32


class TestDeduplicateByHash:
    """Test generic deduplication function."""

    @dataclass
    class Item:
        id: str
        name: str

    def test_removes_duplicates(self) -> None:
        items = [
            self.Item(id="1", name="first"),
            self.Item(id="1", name="second"),
            self.Item(id="2", name="third"),
        ]
        result = deduplicate_by_hash(items, hash_fn=lambda x: x.id)
        assert len(result) == 2

    def test_preserves_order(self) -> None:
        items = [
            self.Item(id="3", name="third"),
            self.Item(id="1", name="first"),
            self.Item(id="2", name="second"),
        ]
        result = deduplicate_by_hash(items, hash_fn=lambda x: x.id)
        assert [i.name for i in result] == ["third", "first", "second"]

    def test_first_seen_wins(self) -> None:
        items = [
            self.Item(id="1", name="winner"),
            self.Item(id="1", name="loser"),
        ]
        result = deduplicate_by_hash(items, hash_fn=lambda x: x.id)
        assert len(result) == 1
        assert result[0].name == "winner"

    def test_empty_list(self) -> None:
        result = deduplicate_by_hash([], hash_fn=lambda x: x)
        assert result == []

    def test_all_unique(self) -> None:
        items = [
            self.Item(id="1", name="a"),
            self.Item(id="2", name="b"),
            self.Item(id="3", name="c"),
        ]
        result = deduplicate_by_hash(items, hash_fn=lambda x: x.id)
        assert len(result) == 3

    def test_all_duplicates(self) -> None:
        items = [
            self.Item(id="1", name="a"),
            self.Item(id="1", name="b"),
            self.Item(id="1", name="c"),
        ]
        result = deduplicate_by_hash(items, hash_fn=lambda x: x.id)
        assert len(result) == 1
        assert result[0].name == "a"
