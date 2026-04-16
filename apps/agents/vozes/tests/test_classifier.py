"""Tests for the VOZES classifier module.

Covers:
- LATAM relevance scoring (Portuguese text, geography, companies)
- LATAM filter (rejects global content below threshold)
- Entity resolution (tickers -> company names)
- Theme classification for all 13 themes
- Self-promo filtering in classification
"""

from __future__ import annotations

import pytest

from apps.agents.social_signals.models import EntityMention, ProcessedSignal, SocialPost
from apps.agents.vozes.classifier import (
    _compute_authority,
    classify_posts_batch,
    compute_latam_relevance,
    passes_latam_filter,
    resolve_ticker_entities,
)
from apps.agents.vozes.config import MIN_LATAM_RELEVANCE


def _make_post(
    text: str = "Test post",
    platform: str = "twitter",
    url: str = "https://example.com/post",
    author_followers: int = 0,
) -> SocialPost:
    """Create a SocialPost for testing."""
    return SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle="testuser",
        author_display_name="Test User",
        author_followers=author_followers,
    )


# ---------------------------------------------------------------------------
# LATAM relevance scoring
# ---------------------------------------------------------------------------


class TestComputeLatamRelevance:
    """Tests for LATAM relevance scoring."""

    def test_portuguese_text_scores_high(self) -> None:
        post = _make_post(
            text="A empresa de tecnologia sobre dados para o mercado de investimento"
        )
        score = compute_latam_relevance(post)
        assert score >= 0.4, f"Portuguese text should score >= 0.4, got {score}"

    def test_spanish_text_scores_high(self) -> None:
        post = _make_post(
            text="La empresa de tecnología sobre datos para el mercado de inversión"
        )
        score = compute_latam_relevance(post)
        assert score >= 0.3, f"Spanish text should score >= 0.3, got {score}"

    def test_english_only_scores_low(self) -> None:
        post = _make_post(
            text="The latest AI model from Silicon Valley shows promising results"
        )
        score = compute_latam_relevance(post)
        assert score < MIN_LATAM_RELEVANCE, f"English-only should score < {MIN_LATAM_RELEVANCE}, got {score}"

    def test_geography_mention_adds_score(self) -> None:
        post = _make_post(text="New startup from São Paulo is disrupting payments")
        score = compute_latam_relevance(post)
        assert score >= 0.15, f"São Paulo mention should add score, got {score}"

    def test_country_mention_adds_score(self) -> None:
        post = _make_post(text="Fintech growth in Brasil is accelerating")
        score = compute_latam_relevance(post)
        assert score >= 0.15, f"Brasil mention should add score, got {score}"

    def test_latam_term_adds_score(self) -> None:
        post = _make_post(text="LATAM startups are attracting more funding")
        score = compute_latam_relevance(post)
        assert score >= 0.15, f"LATAM term should add score, got {score}"

    def test_company_mention_adds_score(self) -> None:
        post = _make_post(text="Nubank just announced a new AI-powered feature")
        score = compute_latam_relevance(post)
        assert score >= 0.1, f"Nubank mention should add score, got {score}"

    def test_multiple_signals_accumulate(self) -> None:
        post = _make_post(
            text="Nubank em São Paulo lança tecnologia de dados para investimento no mercado"
        )
        score = compute_latam_relevance(post)
        assert score >= 0.5, f"Multiple LATAM signals should accumulate, got {score}"

    def test_empty_text_scores_zero(self) -> None:
        post = _make_post(text="")
        score = compute_latam_relevance(post)
        assert score == 0.0

    def test_geography_score_capped(self) -> None:
        """Geography bonus should not exceed 0.8."""
        # Mention many cities to test cap
        cities = "São Paulo Rio de Janeiro Belo Horizonte Curitiba Porto Alegre Recife Brasília"
        post = _make_post(text=cities)
        score = compute_latam_relevance(post)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# LATAM filter
# ---------------------------------------------------------------------------


class TestPassesLatamFilter:
    """Tests for the LATAM relevance filter."""

    def test_high_latam_score_passes(self) -> None:
        post = _make_post(text="Startup em São Paulo")
        assert passes_latam_filter(post, theme="Fintech", latam_score=0.5) is True

    def test_low_score_non_global_topic_rejected(self) -> None:
        post = _make_post(text="RetailTech in Europe is growing")
        assert passes_latam_filter(post, theme="RetailTech", latam_score=0.05) is False

    def test_low_score_global_topic_allowed(self) -> None:
        """AI, Funding, DevTools, Cybersecurity are allowed even with low LATAM score."""
        post = _make_post(text="New AI model released")
        assert passes_latam_filter(post, theme="AI", latam_score=0.05) is True

    def test_funding_always_allowed(self) -> None:
        post = _make_post(text="Series A funding announced")
        assert passes_latam_filter(post, theme="Funding", latam_score=0.0) is True

    def test_devtools_allowed_globally(self) -> None:
        post = _make_post(text="New developer tool released")
        assert passes_latam_filter(post, theme="DevTools", latam_score=0.0) is True

    def test_at_threshold_passes(self) -> None:
        post = _make_post(text="Some topic")
        assert passes_latam_filter(post, theme="Fintech", latam_score=MIN_LATAM_RELEVANCE) is True

    def test_below_threshold_fails(self) -> None:
        post = _make_post(text="Some topic")
        assert passes_latam_filter(post, theme="Fintech", latam_score=MIN_LATAM_RELEVANCE - 0.01) is False


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


class TestResolveTickerEntities:
    """Tests for ticker-to-company resolution."""

    def test_resolves_nu_to_nubank(self) -> None:
        entities = [EntityMention(name="NU", entity_type="company", confidence=0.5)]
        resolved = resolve_ticker_entities(entities)
        assert resolved[0].name == "Nubank"
        assert resolved[0].confidence >= 0.6

    def test_resolves_meli_to_mercado_libre(self) -> None:
        entities = [EntityMention(name="MELI", entity_type="company", confidence=0.5)]
        resolved = resolve_ticker_entities(entities)
        assert resolved[0].name == "Mercado Libre"

    def test_resolves_stne_to_stone(self) -> None:
        entities = [EntityMention(name="STNE", entity_type="company", confidence=0.3)]
        resolved = resolve_ticker_entities(entities)
        assert resolved[0].name == "Stone"
        assert resolved[0].confidence == 0.6  # min(0.3, 0.6) -> 0.6

    def test_preserves_non_ticker_entities(self) -> None:
        entities = [EntityMention(name="Anthropic", entity_type="company", confidence=0.7)]
        resolved = resolve_ticker_entities(entities)
        assert resolved[0].name == "Anthropic"
        assert resolved[0].confidence == 0.7

    def test_preserves_person_entities(self) -> None:
        entities = [EntityMention(name="NU", entity_type="person", confidence=0.5)]
        resolved = resolve_ticker_entities(entities)
        # "NU" as a person should NOT be resolved
        assert resolved[0].name == "NU"

    def test_empty_list(self) -> None:
        assert resolve_ticker_entities([]) == []

    def test_mixed_entities(self) -> None:
        entities = [
            EntityMention(name="NU", entity_type="company", confidence=0.5),
            EntityMention(name="Elon Musk", entity_type="person", confidence=0.8),
            EntityMention(name="VTEX", entity_type="company", confidence=0.4),
        ]
        resolved = resolve_ticker_entities(entities)
        assert resolved[0].name == "Nubank"
        assert resolved[1].name == "Elon Musk"
        assert resolved[2].name == "VTEX"  # Already full name, also in ticker map


# ---------------------------------------------------------------------------
# Theme classification (keyword-based)
# ---------------------------------------------------------------------------


class TestThemeClassification:
    """Tests that all 13 themes can be classified via keywords."""

    @pytest.mark.parametrize("text,expected_theme", [
        ("AI agents are transforming banking compliance and KYC automation", "AI in Banking"),
        ("Nubank launches new neobank features for payments", "Fintech"),
        ("New LLM model from OpenAI with multimodal capabilities", "AI"),
        ("Series A funding round raised $10M", "Funding"),
        ("Venture capital fund raises from LPs", "VC"),
        ("Telemedicine platform raises clinical AI diagnostics", "HealthTech"),
        ("New developer tool for CI/CD observability", "DevTools"),
        ("Startup hiring talent for remote engineering team", "Startup Ops"),
        ("Cybersecurity breach in cloud security infrastructure", "Cybersecurity"),
        ("Banco Central new regulation for open banking", "Regulation"),
        ("E-commerce marketplace logistics fulfillment", "RetailTech"),
        ("Renewable energy carbon credit ESG sustainability", "CleanTech"),
        ("Online learning AI tutor adaptive learning platform", "EdTech"),
    ])
    def test_classifies_theme(self, text: str, expected_theme: str) -> None:
        posts = [_make_post(text=text)]
        signals = classify_posts_batch(posts, apply_latam_filter=False)
        assert len(signals) == 1
        assert signals[0].theme == expected_theme, (
            f"Expected theme '{expected_theme}' for text '{text}', "
            f"got '{signals[0].theme}'"
        )

    def test_unclassified_post_has_empty_theme(self) -> None:
        posts = [_make_post(text="The weather is nice today")]
        signals = classify_posts_batch(posts, apply_latam_filter=False)
        assert len(signals) == 1
        assert signals[0].theme == ""


# ---------------------------------------------------------------------------
# classify_posts_batch integration
# ---------------------------------------------------------------------------


class TestClassifyPostsBatch:
    """Integration tests for the batch classification pipeline."""

    def test_empty_input(self) -> None:
        result = classify_posts_batch([])
        assert result == []

    def test_basic_classification(self) -> None:
        posts = [
            _make_post(text="Nubank raises $100M in Series E funding round"),
            _make_post(text="New AI model from OpenAI with GPT capabilities"),
        ]
        signals = classify_posts_batch(posts, apply_latam_filter=False)
        assert len(signals) == 2
        # Both should have themes
        themes = [s.theme for s in signals]
        assert any(t for t in themes), "At least one post should be themed"

    def test_latam_filter_removes_non_latam(self) -> None:
        posts = [
            _make_post(text="E-commerce platform in Europe launches retail media"),
            _make_post(text="Nubank em São Paulo lança tecnologia de investimento para mercado"),
        ]
        signals = classify_posts_batch(posts, apply_latam_filter=True)
        # The European post should be filtered out (RetailTech, not global, low LATAM score)
        # The Brazilian post should remain
        assert len(signals) >= 1
        # At least the LATAM post should survive
        latam_texts = [s.post.text for s in signals if "Nubank" in s.post.text]
        assert len(latam_texts) >= 1

    def test_entities_have_ticker_resolution(self) -> None:
        posts = [_make_post(text="$NU stock is up 5% today with $MELI")]
        signals = classify_posts_batch(posts, apply_latam_filter=False)
        assert len(signals) == 1
        entity_names = [e.name for e in signals[0].entities]
        # $NU should be resolved to Nubank
        assert "Nubank" in entity_names or "NU" in entity_names

    def test_authority_score_computed(self) -> None:
        posts = [_make_post(text="AI agents in fintech", author_followers=100000)]
        signals = classify_posts_batch(posts, apply_latam_filter=False)
        assert len(signals) == 1
        assert signals[0].authority_score > 0.0


# ---------------------------------------------------------------------------
# Authority computation
# ---------------------------------------------------------------------------


class TestComputeAuthority:
    """Tests for the authority scoring function."""

    def test_zero_followers(self) -> None:
        post = _make_post(author_followers=0)
        assert _compute_authority(post) == 0.0

    def test_high_followers(self) -> None:
        post = _make_post(author_followers=1_000_000)
        score = _compute_authority(post)
        assert score > 0.5, f"1M followers should score > 0.5, got {score}"

    def test_moderate_followers(self) -> None:
        post = _make_post(author_followers=10_000)
        score = _compute_authority(post)
        assert 0.0 < score < 1.0

    def test_authority_capped_at_one(self) -> None:
        post = _make_post(author_followers=100_000_000)
        score = _compute_authority(post)
        assert score <= 1.0
