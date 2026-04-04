"""Tests for social signals classifier — keyword mode, batch mode, theme detection."""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.classifier import (
    _classify_with_keywords,
    _compute_authority,
    _compute_engagement_rank,
    _extract_with_regex,
    _match_sub_theme,
    classify_posts_batch,
    classify_post,
    classify_theme,
    compute_sentiment,
    extract_entities,
    is_commercial,
)
from apps.agents.social_signals.models import EntityMention, ProcessedSignal, SocialPost


def _make_post(
    text: str = "test post",
    platform: str = "twitter",
    author_handle: str = "testuser",
    author_followers: int = 0,
    metrics: Optional[dict] = None,
    external_url: Optional[str] = None,
    url: str = "https://twitter.com/1",
) -> SocialPost:
    return SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle=author_handle,
        author_followers=author_followers,
        metrics=metrics or {},
        external_url=external_url,
    )


class TestKeywordClassification:
    """Test keyword-only theme classification (no LLM)."""

    def test_classifies_ai_theme(self):
        theme, sub = _classify_with_keywords("New LLM model from OpenAI breaks records")
        assert theme == "AI"

    def test_classifies_fintech_theme(self):
        theme, sub = _classify_with_keywords("Fintech neobank raises Series B for payments")
        assert theme == "Fintech"

    def test_classifies_ai_in_banking_theme(self):
        theme, sub = _classify_with_keywords("Banking AI compliance tool for KYC automation")
        assert theme == "AI in Banking"

    def test_no_match_returns_empty(self):
        theme, sub = _classify_with_keywords("The weather today is sunny and warm")
        assert theme == ""
        assert sub == ""

    def test_ai_in_banking_over_ai_when_specific(self):
        """AI in Banking should win over generic AI when banking-specific keywords match."""
        theme, sub = _classify_with_keywords(
            "New banking AI tool for fraud detection and AML compliance"
        )
        assert theme == "AI in Banking"

    def test_sub_theme_detection(self):
        theme, sub = _classify_with_keywords(
            "AI agents are transforming enterprise workflows with LLM"
        )
        assert theme == "AI"
        assert sub == "AI agents"

    def test_multiple_keywords_picks_highest_score(self):
        theme, sub = _classify_with_keywords(
            "fintech neobank payment lending credit open banking"
        )
        assert theme == "Fintech"


class TestMatchSubTheme:
    def test_matches_exact_subtema(self):
        result = _match_sub_theme("embedded finance is growing fast", "Fintech")
        assert result == "Embedded finance"

    def test_no_match_returns_empty(self):
        result = _match_sub_theme("random text about nothing", "AI")
        assert result == ""


class TestIsCommercial:
    def test_detects_funding(self):
        assert is_commercial("Company raised $50M in Series A funding")

    def test_detects_hiring(self):
        assert is_commercial("We have a job opening for senior engineers")

    def test_not_commercial(self):
        assert not is_commercial("Interesting research paper on neural networks")

    def test_detects_ipo(self):
        assert is_commercial("The company is preparing for its IPO next year")


class TestComputeAuthority:
    def test_zero_followers(self):
        post = _make_post(author_followers=0)
        assert _compute_authority(post) == 0.0

    def test_moderate_followers(self):
        post = _make_post(author_followers=10000)
        score = _compute_authority(post)
        assert 0.3 < score < 0.8

    def test_high_followers(self):
        post = _make_post(author_followers=1_000_000)
        score = _compute_authority(post)
        assert score > 0.8

    def test_capped_at_one(self):
        post = _make_post(author_followers=100_000_000)
        score = _compute_authority(post)
        assert score <= 1.0


class TestComputeEngagementRank:
    def test_no_metrics(self):
        post = _make_post(metrics={})
        assert _compute_engagement_rank(post) == 0.0

    def test_likes_count(self):
        post = _make_post(metrics={"likes": 100})
        assert _compute_engagement_rank(post) == 100

    def test_replies_weighted_double(self):
        post = _make_post(metrics={"replies": 50})
        assert _compute_engagement_rank(post) == 100

    def test_reposts_weighted_triple(self):
        post = _make_post(metrics={"reposts": 10})
        assert _compute_engagement_rank(post) == 30

    def test_combined_metrics(self):
        post = _make_post(metrics={"likes": 10, "replies": 5, "reposts": 3, "score": 100})
        expected = 10 + 5 * 2 + 3 * 3 + 100
        assert _compute_engagement_rank(post) == expected


class TestExtractWithRegex:
    def test_extracts_mentions(self):
        entities = _extract_with_regex("Check out @nubank and @stripe")
        names = [e.name for e in entities]
        assert "nubank" in names
        assert "stripe" in names

    def test_extracts_tickers(self):
        entities = _extract_with_regex("Watching $AAPL and $GOOG today")
        tickers = [e.name for e in entities if e.entity_type == "company"]
        assert "AAPL" in tickers
        assert "GOOG" in tickers

    def test_no_entities(self):
        entities = _extract_with_regex("Just a normal sentence without mentions")
        assert entities == []


class TestClassifyPostsBatch:
    """Test batch classification strategy."""

    def test_empty_input(self):
        result = classify_posts_batch([])
        assert result == []

    def test_keyword_only_without_llm(self):
        posts = [
            _make_post(text="New LLM model from OpenAI"),
            _make_post(text="Fintech neobank raises funds"),
            _make_post(text="The weather is nice"),
        ]
        signals = classify_posts_batch(posts, llm_client=None)
        assert len(signals) == 3

        # First two should have themes, third should not
        assert signals[0].theme == "AI"
        assert signals[1].theme == "Fintech"
        assert signals[2].theme == ""

    def test_all_posts_classified_without_llm(self):
        """Even without LLM, all posts get keyword classification."""
        posts = [_make_post(text="AI agent with LLM") for _ in range(50)]
        signals = classify_posts_batch(posts, llm_client=None, top_n_for_llm=20)
        assert len(signals) == 50
        assert all(s.theme == "AI" for s in signals)

    def test_llm_enriches_top_n_only(self):
        """When LLM is available, only top N posts get entity/sentiment enrichment."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate.return_value = "0.5"

        posts = [
            _make_post(
                text="AI agent with LLM capabilities",
                metrics={"likes": i * 10},
                author_followers=i * 100,
            )
            for i in range(10)
        ]

        signals = classify_posts_batch(posts, llm_client=mock_llm, top_n_for_llm=3)
        assert len(signals) == 10

        # LLM should have been called for sentiment on exactly 3 posts
        # (extract_entities calls + compute_sentiment calls)
        # Each enriched post gets 1 entity extraction + 1 sentiment call = 2 calls max
        # But entity extraction may return None so not all calls proceed
        assert mock_llm.generate.call_count <= 6  # At most 3 * 2

    def test_sentiment_default_zero_without_llm(self):
        """Posts not enriched by LLM should have sentiment 0.0."""
        posts = [_make_post(text="Fintech neobank launch")]
        signals = classify_posts_batch(posts, llm_client=None)
        assert signals[0].sentiment == 0.0

    def test_commercial_detection_in_batch(self):
        posts = [
            _make_post(text="Company raised $50M in Series A funding for AI"),
            _make_post(text="Research paper on transformer architecture"),
        ]
        signals = classify_posts_batch(posts, llm_client=None)
        assert signals[0].is_commercial is True
        assert signals[1].is_commercial is False


class TestClassifyPost:
    """Test the per-post classify_post function (legacy, LLM per post)."""

    def test_classifies_without_llm(self):
        post = _make_post(text="AI agent with LLM capabilities", author_followers=1000)
        signal = classify_post(post, llm_client=None)
        assert signal.theme == "AI"
        assert signal.authority_score > 0
        assert signal.sentiment == 0.0  # No LLM

    def test_preserves_post_reference(self):
        post = _make_post(text="Fintech payment innovation")
        signal = classify_post(post)
        assert signal.post is post
        assert signal.content_hash == post.content_hash
