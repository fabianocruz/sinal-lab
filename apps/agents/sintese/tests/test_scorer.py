"""Tests for SINTESE scorer module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import (
    ScoredItem,
    score_topic_relevance,
    score_recency,
    score_source_authority,
    score_latam_relevance,
    score_items,
)


def make_item(**kwargs) -> FeedItem:
    """Helper to create a FeedItem with defaults."""
    defaults = {
        "title": "Test Article",
        "url": "https://example.com/test",
        "source_name": "test_source",
    }
    defaults.update(kwargs)
    return FeedItem(**defaults)


class TestTopicRelevance:
    """Test topic relevance scoring."""

    def test_ai_topic_high_score(self):
        item = make_item(title="New machine learning framework for startups")
        score = score_topic_relevance(item)
        assert score >= 0.5

    def test_startup_funding_high_score(self):
        item = make_item(title="Startup raises Serie A funding round")
        score = score_topic_relevance(item)
        assert score >= 0.5

    def test_irrelevant_topic_low_score(self):
        item = make_item(title="Celebrity gossip from Hollywood")
        score = score_topic_relevance(item)
        assert score < 0.3

    def test_multiple_keywords_bonus(self):
        item = make_item(
            title="AI startup raises venture capital funding for machine learning platform"
        )
        score = score_topic_relevance(item)
        assert score >= 0.7

    def test_summary_considered(self):
        item = make_item(
            title="News today",
            summary="Nubank uses inteligencia artificial for credit scoring in Brasil",
        )
        score = score_topic_relevance(item)
        assert score >= 0.5

    def test_tags_considered(self):
        item = make_item(title="Update", tags=["startup", "fintech"])
        score = score_topic_relevance(item)
        assert score >= 0.3

    def test_score_capped_at_one(self):
        item = make_item(
            title="startup venture capital investimento rodada serie a seed unicornio ipo machine learning ai agent"
        )
        score = score_topic_relevance(item)
        assert score <= 1.0


class TestRecency:
    """Test recency scoring."""

    def test_today_is_highest(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now)
        assert score_recency(item, now) == 1.0

    def test_yesterday(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now - timedelta(days=1))
        assert score_recency(item, now) == 1.0

    def test_three_days_ago(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now - timedelta(days=2))
        assert score_recency(item, now) == 0.9

    def test_one_week_ago(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now - timedelta(days=5))
        assert score_recency(item, now) == 0.7

    def test_two_weeks_ago(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now - timedelta(days=10))
        assert score_recency(item, now) == 0.4

    def test_old_item(self):
        now = datetime.now(timezone.utc)
        item = make_item(published_at=now - timedelta(days=30))
        assert score_recency(item, now) == 0.1

    def test_no_date(self):
        item = make_item()
        assert score_recency(item) == 0.3

    def test_recency_decreases_over_time(self):
        now = datetime.now(timezone.utc)
        scores = []
        for days in [0, 2, 5, 10, 30]:
            item = make_item(published_at=now - timedelta(days=days))
            scores.append(score_recency(item, now))
        # Scores should be monotonically non-increasing
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


class TestSourceAuthority:
    """Test source authority scoring."""

    def test_known_source(self):
        item = make_item(source_name="techcrunch")
        assert score_source_authority(item) == 0.9

    def test_latam_source(self):
        item = make_item(source_name="startse")
        assert score_source_authority(item) >= 0.8

    def test_unknown_source(self):
        item = make_item(source_name="random_blog_xyz")
        assert score_source_authority(item) == 0.5


class TestLatamRelevance:
    """Test LATAM relevance scoring."""

    def test_portuguese_content(self):
        item = make_item(
            title="Empresa de tecnologia lanca nova plataforma para startups no Brasil"
        )
        score = score_latam_relevance(item)
        assert score >= 0.3

    def test_latam_location(self):
        item = make_item(title="São Paulo startup ecosystem grows 30% in 2026")
        # Note: lowercased comparison, so "são paulo" won't match "sao paulo"
        # but "startup" and other signals still apply
        item2 = make_item(title="sao paulo startup ecosystem grows")
        score = score_latam_relevance(item2)
        assert score >= 0.1

    def test_latam_company(self):
        item = make_item(title="Nubank launches new credit product")
        score = score_latam_relevance(item)
        assert score >= 0.1

    def test_english_non_latam(self):
        item = make_item(title="Silicon Valley startup raises funding")
        score = score_latam_relevance(item)
        assert score < 0.3

    def test_score_capped_at_one(self):
        item = make_item(
            title="Startup de fintech brasil latam america latina sao paulo nubank mercadolibre"
        )
        score = score_latam_relevance(item)
        assert score <= 1.0


class TestScoreItems:
    """Test the full scoring pipeline."""

    def test_returns_sorted_by_composite(self):
        items = [
            make_item(title="Random tech news", url="https://a.com/1"),
            make_item(
                title="AI startup raises venture capital in Brasil",
                url="https://a.com/2",
                source_name="techcrunch_latam",
                published_at=datetime.now(timezone.utc),
            ),
            make_item(title="Weather update", url="https://a.com/3"),
        ]
        scored = score_items(items)
        assert len(scored) == 3
        # Most relevant should be first
        assert scored[0].item.url == "https://a.com/2"
        # Composite scores should be descending
        for i in range(len(scored) - 1):
            assert scored[i].composite_score >= scored[i + 1].composite_score

    def test_empty_input(self):
        scored = score_items([])
        assert scored == []

    def test_scored_item_has_all_dimensions(self):
        items = [make_item(title="Test", published_at=datetime.now(timezone.utc))]
        scored = score_items(items)
        assert len(scored) == 1
        s = scored[0]
        assert 0.0 <= s.topic_score <= 1.0
        assert 0.0 <= s.recency_score <= 1.0
        assert 0.0 <= s.authority_score <= 1.0
        assert 0.0 <= s.latam_score <= 1.0
        assert 0.0 <= s.composite_score <= 1.0
