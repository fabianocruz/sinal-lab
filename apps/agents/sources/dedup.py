"""Shared deduplication utilities for agent collectors.

Replaces 5 copies of inline MD5 hashing and dedup loops across collectors.

Usage:
    from apps.agents.sources.dedup import compute_content_hash, deduplicate_by_hash

    hash = compute_content_hash(url)
    unique_items = deduplicate_by_hash(items, hash_fn=lambda x: x.content_hash)
"""

import hashlib
from typing import Callable, List, Sequence, TypeVar

T = TypeVar("T")


def compute_content_hash(url: str) -> str:
    """Compute MD5 hash of a URL for deduplication.

    Args:
        url: The URL to hash.

    Returns:
        32-character hex digest string.
    """
    return hashlib.md5(url.encode()).hexdigest()


def compute_composite_hash(*parts: str) -> str:
    """Compute MD5 hash of multiple parts joined by '-'.

    Used for composite keys (e.g., funding events: company+round+url).

    Args:
        parts: String parts to join and hash.

    Returns:
        32-character hex digest string.
    """
    composite = "-".join(parts)
    return hashlib.md5(composite.encode()).hexdigest()


def deduplicate_by_hash(
    items: Sequence[T],
    hash_fn: Callable[[T], str],
) -> List[T]:
    """Deduplicate a sequence by a hash function. First-seen wins.

    Args:
        items: Sequence of items to deduplicate.
        hash_fn: Function that extracts a hash string from each item.

    Returns:
        List of unique items, preserving original order.
    """
    seen: set = set()
    unique: List[T] = []

    for item in items:
        h = hash_fn(item)
        if h not in seen:
            seen.add(h)
            unique.append(item)

    return unique
