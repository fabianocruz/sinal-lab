"""Tests for SINTESE scorer module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import (
    MIN_TOPIC_SCORE,
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

    def test_no_substring_false_positive_ai(self):
        """'ai' should NOT match as substring in Portuguese words like 'custaria'."""
        item = make_item(title="Quanto custaria um Corsa sedan Classic hoje")
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_no_substring_false_positive_api(self):
        """'api' should NOT match as substring in words like 'replicar'."""
        item = make_item(title="Como replicar receitas tradicionais em casa")
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_no_substring_false_positive_inter(self):
        """'inter' (editorial keyword) should NOT match in 'internet'."""
        item = make_item(title="Internet speed test results for 2026")
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_standalone_ai_keyword_matches(self):
        """'ai' as a standalone word should match correctly."""
        item = make_item(title="Using ai for credit scoring in production")
        score = score_topic_relevance(item)
        assert score >= 0.5

    def test_consumer_gadget_filtered(self):
        """Consumer electronics with no tech relevance should score zero."""
        item = make_item(title="Celular resistente a agua melhor opcao 2026")
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_sports_event_filtered(self):
        """Sports events should score zero even from financial sources."""
        item = make_item(title="Rio Open 2026 tenistas confirmados")
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_geographic_brasil_not_in_topic(self):
        """'brasil' alone should NOT give topic relevance (it's geographic, not topical)."""
        item = make_item(
            title="Produto lancado no Brasil em novembro",
            summary="Disponivel em todo o Brasil",
        )
        score = score_topic_relevance(item)
        assert score == 0.0

    def test_brasil_with_tech_topic_scores(self):
        """'brasil' + tech keyword should score via the tech keyword, not geography."""
        item = make_item(title="Fintech startup raises seed round in latam")
        score = score_topic_relevance(item)
        assert score >= 0.5


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

    def test_inter_not_matched_in_internet(self):
        """'inter' (Banco Inter) should NOT match as substring in 'internet'."""
        item = make_item(title="Internet speed increased globally")
        score = score_latam_relevance(item)
        assert score == 0.0

    def test_inter_matched_standalone(self):
        """'inter' as standalone should match (Banco Inter)."""
        item = make_item(title="Banco inter launches new product")
        score = score_latam_relevance(item)
        assert score >= 0.1


class TestScoreItems:
    """Test the full scoring pipeline."""

    def test_returns_sorted_by_composite(self):
        items = [
            make_item(title="Cloud kubernetes devops infrastructure", url="https://a.com/1"),
            make_item(
                title="AI startup raises venture capital in Brasil",
                url="https://a.com/2",
                source_name="techcrunch_latam",
                published_at=datetime.now(timezone.utc),
            ),
            make_item(title="Fintech startup in latam ecosystem", url="https://a.com/3"),
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
        items = [make_item(
            title="Machine learning startup funding",
            published_at=datetime.now(timezone.utc),
        )]
        scored = score_items(items)
        assert len(scored) == 1
        s = scored[0]
        assert 0.0 <= s.topic_score <= 1.0
        assert 0.0 <= s.recency_score <= 1.0
        assert 0.0 <= s.authority_score <= 1.0
        assert 0.0 <= s.latam_score <= 1.0
        assert 0.0 <= s.composite_score <= 1.0

    def test_filters_zero_topic_relevance(self):
        """Items with no topic relevance should be filtered out."""
        items = [
            make_item(title="Celebrity gossip from Hollywood", url="https://a.com/1"),
            make_item(title="Weather update for today", url="https://a.com/2"),
            make_item(title="Quanto custaria um Corsa sedan Classic", url="https://a.com/3"),
            make_item(
                title="AI startup raises venture capital",
                url="https://a.com/4",
                published_at=datetime.now(timezone.utc),
            ),
        ]
        scored = score_items(items)
        # Only the AI startup item should survive
        assert len(scored) == 1
        assert scored[0].item.url == "https://a.com/4"

    def test_min_topic_score_bypass(self):
        """Setting min_topic_score=0 disables the filter."""
        items = [
            make_item(title="Completely irrelevant article"),
            make_item(title="AI startup funding"),
        ]
        scored = score_items(items, min_topic_score=0.0)
        assert len(scored) == 2

    def test_editorial_keywords_recognized(self):
        """Items matching editorial territory keywords should pass the filter."""
        items = [
            make_item(title="Open banking portabilidade no Brasil"),
            make_item(title="Tokenização de real world assets com blockchain"),
        ]
        scored = score_items(items)
        assert len(scored) == 2
        for s in scored:
            assert s.topic_score >= MIN_TOPIC_SCORE


class TestSourceCalibration:
    """Test source authority calibration and config alignment."""

    REMOVED_SOURCES = {
        "canaltech", "tecmundo", "olhardigital", "tecnoblog",
        "mundoconectado", "meiobit", "gabordi",
    }

    def test_removed_sources_not_in_config(self):
        """Consumer tech sources must NOT appear in SINTESE config."""
        from apps.agents.sintese.config import LATAM_TECH_FEEDS

        config_names = {s.name for s in LATAM_TECH_FEEDS}
        overlap = self.REMOVED_SOURCES & config_names
        assert overlap == set(), f"Removed sources still in config: {overlap}"

    def test_all_config_sources_have_authority(self):
        """Every source in SINTESE config must have an explicit authority score."""
        from apps.agents.sintese.config import LATAM_TECH_FEEDS
        from apps.agents.sintese.scorer import SOURCE_AUTHORITY

        config_names = {s.name for s in LATAM_TECH_FEEDS}
        missing = config_names - set(SOURCE_AUTHORITY.keys())
        assert missing == set(), f"Sources without authority score: {missing}"

    def test_authority_scores_in_valid_range(self):
        """All authority scores must be between 0.0 and 1.0."""
        from apps.agents.sintese.scorer import SOURCE_AUTHORITY

        for source, score in SOURCE_AUTHORITY.items():
            assert 0.0 <= score <= 1.0, f"{source} has invalid authority: {score}"

    def test_infomoney_authority_lowered(self):
        """Infomoney should have a reduced authority score (too much general finance)."""
        from apps.agents.sintese.scorer import SOURCE_AUTHORITY

        assert SOURCE_AUTHORITY["infomoney"] <= 0.6

    NEW_QUALITY_SOURCES = {
        "wired", "geekwire", "cnbc_tech", "pragmatic_engineer",
        "simonwillison", "a16z", "ycombinator", "first_round",
        "crunchbase_news", "fintech_nexus",
    }

    def test_new_sources_in_config(self):
        """All new quality sources must be present in SINTESE config."""
        from apps.agents.sintese.config import LATAM_TECH_FEEDS

        config_names = {s.name for s in LATAM_TECH_FEEDS}
        missing = self.NEW_QUALITY_SOURCES - config_names
        assert missing == set(), f"New sources missing from config: {missing}"

    def test_new_sources_have_authority(self):
        """Every new source must have an explicit authority score."""
        from apps.agents.sintese.scorer import SOURCE_AUTHORITY

        missing = self.NEW_QUALITY_SOURCES - set(SOURCE_AUTHORITY.keys())
        assert missing == set(), f"New sources without authority score: {missing}"

    def test_new_sources_authority_calibrated(self):
        """New quality sources should have authority >= 0.7 (they were selected for quality)."""
        from apps.agents.sintese.scorer import SOURCE_AUTHORITY

        for source in self.NEW_QUALITY_SOURCES:
            score = SOURCE_AUTHORITY.get(source, 0.0)
            assert score >= 0.7, f"{source} authority too low: {score}"
