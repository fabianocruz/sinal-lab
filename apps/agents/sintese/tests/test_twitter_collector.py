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
