"""Tests for SINTESE Twitter collector module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import hashlib
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from packages.editorial.guidelines import EDITORIAL_TERRITORIES


# ---------------------------------------------------------------------------
# Query Builder Tests
# ---------------------------------------------------------------------------

class TestBuildTwitterQueries:
    """Test Twitter query builder."""

    def test_builds_one_query_per_territory(self):
        from apps.agents.sintese.twitter_collector import build_twitter_queries

        queries = build_twitter_queries()
        assert isinstance(queries, dict)
        assert set(queries.keys()) == set(EDITORIAL_TERRITORIES.keys())

    def test_query_contains_has_links(self):
        from apps.agents.sintese.twitter_collector import build_twitter_queries

        queries = build_twitter_queries()
        for territory, query in queries.items():
            assert "has:links" in query, f"{territory} query missing has:links"
            assert "-is:retweet" in query, f"{territory} query missing -is:retweet"

    def test_query_under_512_chars(self):
        from apps.agents.sintese.twitter_collector import build_twitter_queries

        queries = build_twitter_queries()
        for territory, query in queries.items():
            assert len(query) <= 512, (
                f"{territory} query is {len(query)} chars (max 512)"
            )

    def test_query_keywords_from_editorial(self):
        from apps.agents.sintese.twitter_collector import build_twitter_queries

        queries = build_twitter_queries()
        # Each query should contain at least one keyword from its territory
        for territory_key, query in queries.items():
            territory_keywords = EDITORIAL_TERRITORIES[territory_key]["keywords"]
            query_lower = query.lower()
            has_keyword = any(
                kw.lower() in query_lower for kw in territory_keywords
            )
            assert has_keyword, (
                f"{territory_key} query has no keywords from its editorial territory"
            )

    def test_query_includes_language_filter(self):
        from apps.agents.sintese.twitter_collector import build_twitter_queries

        queries = build_twitter_queries()
        for territory, query in queries.items():
            assert "lang:en" in query or "lang:pt" in query, (
                f"{territory} query missing language filter"
            )


# ---------------------------------------------------------------------------
# Sample X API v2 response data for tests
# ---------------------------------------------------------------------------

SAMPLE_TWEET_WITH_LINK = {
    "id": "1892345678901234567",
    "text": "Great analysis of open banking in LATAM https://t.co/abc123",
    "created_at": "2026-02-17T10:30:00.000Z",
    "author_id": "111222333",
    "entities": {
        "urls": [
            {
                "start": 40,
                "end": 63,
                "url": "https://t.co/abc123",
                "expanded_url": "https://techcrunch.com/2026/02/17/open-banking-latam/",
                "display_url": "techcrunch.com/2026/02/17/ope...",
            }
        ]
    },
}

SAMPLE_TWEET_NO_LINK = {
    "id": "1892345678901234999",
    "text": "AI agents are going to transform fintech in Brazil",
    "created_at": "2026-02-16T08:00:00.000Z",
    "author_id": "444555666",
}

SAMPLE_TWEET_LONG_TEXT = {
    "id": "1892345678901235000",
    "text": "x" * 1500,
    "created_at": "2026-02-15T12:00:00.000Z",
    "author_id": "777888999",
}

SAMPLE_USERS = {
    "111222333": {"id": "111222333", "name": "Tech Analyst", "username": "techanalyst"},
    "444555666": {"id": "444555666", "name": "VC Partner", "username": "vcpartner"},
    "777888999": {"id": "777888999", "name": "Dev Writer", "username": "devwriter"},
}


# ---------------------------------------------------------------------------
# Tweet Parser Tests
# ---------------------------------------------------------------------------

class TestParseTweet:
    """Test tweet JSON to FeedItem parsing."""

    def test_parse_tweet_with_expanded_url(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", SAMPLE_USERS)
        assert item is not None
        assert item.url == "https://techcrunch.com/2026/02/17/open-banking-latam/"

    def test_parse_tweet_without_links_returns_tweet_url(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_NO_LINK, "twitter_ai", SAMPLE_USERS)
        assert item is not None
        assert "1892345678901234999" in item.url
        assert "twitter.com" in item.url or "x.com" in item.url

    def test_content_hash_from_expanded_url(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", SAMPLE_USERS)
        assert item is not None
        expected_hash = hashlib.md5(
            "https://techcrunch.com/2026/02/17/open-banking-latam/".encode()
        ).hexdigest()
        assert item.content_hash == expected_hash

    def test_parse_tweet_extracts_author(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", SAMPLE_USERS)
        assert item is not None
        assert item.author == "@techanalyst"

    def test_parse_tweet_extracts_date(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", SAMPLE_USERS)
        assert item is not None
        assert item.published_at is not None
        assert item.published_at.year == 2026
        assert item.published_at.month == 2
        assert item.published_at.day == 17

    def test_parse_tweet_truncates_long_text(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_LONG_TEXT, "twitter_ai", SAMPLE_USERS)
        assert item is not None
        assert len(item.summary) <= 1003  # 1000 + "..."

    def test_parse_tweet_source_name(self):
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", SAMPLE_USERS)
        assert item is not None
        assert item.source_name == "twitter_fintech"

    def test_parse_tweet_missing_author_id(self):
        """Tweet with author_id not in users dict should still parse."""
        from apps.agents.sintese.twitter_collector import parse_tweet

        item = parse_tweet(SAMPLE_TWEET_WITH_LINK, "twitter_fintech", {})
        assert item is not None
        assert item.author is None or item.author == ""
