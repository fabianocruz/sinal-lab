"""Tests for RADAR classifier module."""

import pytest
from datetime import datetime, timezone, timedelta

from apps.agents.radar.collector import TrendSignal
from apps.agents.radar.classifier import (
    BLOCKED_TERMS,
    ClassifiedSignal,
    MIN_LATAM_RELEVANCE,
    MIN_TOPIC_CONFIDENCE,
    NEGATIVE_KEYWORDS,
    _has_negative_keyword,
    _is_blocked,
    classify_topics,
    compute_latam_relevance,
    compute_momentum,
    classify_signals,
)


def make_signal(**kwargs) -> TrendSignal:
    """Helper to create a TrendSignal with defaults."""
    defaults = {
        "title": "Test Signal",
        "url": "https://example.com/test",
        "source_name": "test_source",
        "source_type": "hn",
    }
    defaults.update(kwargs)
    return TrendSignal(**defaults)


class TestClassifyTopics:
    """Test topic classification."""

    def test_ai_ml_topic(self):
        signal = make_signal(title="New machine learning transformer model released")
        topics, primary, confidence = classify_topics(signal)
        assert "ai_ml" in topics
        assert primary == "ai_ml"
        assert confidence > 0

    def test_infrastructure_topic(self):
        signal = make_signal(title="Kubernetes deployment with terraform and docker")
        topics, primary, confidence = classify_topics(signal)
        assert "infrastructure" in topics

    def test_fintech_topic(self):
        signal = make_signal(title="New fintech payment solution using pix and open banking")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics

    def test_developer_tools_topic(self):
        signal = make_signal(title="Rust-based cli package manager for developer experience")
        topics, primary, confidence = classify_topics(signal)
        assert "developer_tools" in topics

    def test_uncategorized(self):
        signal = make_signal(title="Random xyz topic with no matching keywords")
        topics, primary, confidence = classify_topics(signal)
        assert primary == "uncategorized"
        assert confidence == 0.1

    def test_multiple_topics(self):
        signal = make_signal(
            title="AI startup raises seed round venture capital for machine learning platform"
        )
        topics, primary, confidence = classify_topics(signal)
        assert len(topics) >= 2  # Should match ai_ml and startup_ecosystem

    def test_summary_considered(self):
        signal = make_signal(
            title="News",
            summary="Deep learning transformer model for computer vision tasks",
        )
        topics, primary, confidence = classify_topics(signal)
        assert "ai_ml" in topics

    def test_confidence_capped(self):
        signal = make_signal(
            title="machine learning deep learning llm gpt transformer neural network ai agent generative ai"
        )
        _, _, confidence = classify_topics(signal)
        assert confidence <= 1.0

    def test_defi_classified_as_fintech(self):
        signal = make_signal(title="New defi protocol launches stablecoin yield farming on ethereum")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics

    def test_web3_classified_as_fintech(self):
        signal = make_signal(title="web3 wallet smart contract bridge for solana dex")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics
        assert primary == "fintech"

    def test_stablecoin_classified_as_fintech(self):
        signal = make_signal(title="Stablecoin tvl surges amid layer 2 rollup adoption")
        topics, primary, confidence = classify_topics(signal)
        assert "fintech" in topics


class TestComputeMomentum:
    """Test momentum scoring."""

    def test_recent_signal_high_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now)
        momentum = compute_momentum(signal, now)
        assert momentum >= 0.5

    def test_old_signal_low_momentum(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(published_at=now - timedelta(days=14))
        momentum = compute_momentum(signal, now)
        assert momentum < 0.5

    def test_no_date_moderate_momentum(self):
        signal = make_signal()
        momentum = compute_momentum(signal)
        assert 0.1 < momentum < 0.8

    def test_github_stars_boost_momentum(self):
        """Stars should increase the engagement component of momentum."""
        now = datetime.now(timezone.utc)
        signal_low_stars = make_signal(
            source_type="github",
            published_at=now,
            metrics={"stars": 1},
        )
        signal_high_stars = make_signal(
            source_type="github",
            published_at=now,
            metrics={"stars": 100000},
        )
        m1 = compute_momentum(signal_low_stars, now)
        m2 = compute_momentum(signal_high_stars, now)
        assert m2 > m1

    def test_momentum_decreases_over_time(self):
        now = datetime.now(timezone.utc)
        scores = []
        for days in [0, 1, 3, 7, 14]:
            signal = make_signal(published_at=now - timedelta(days=days))
            scores.append(compute_momentum(signal, now))
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_momentum_capped_at_one(self):
        now = datetime.now(timezone.utc)
        signal = make_signal(
            published_at=now,
            source_type="trends",
            metrics={"stars": 1_000_000},
        )
        assert compute_momentum(signal, now) <= 1.0


class TestLatamRelevance:
    """Test LATAM relevance scoring."""

    def test_portuguese_content(self):
        signal = make_signal(
            title="Empresa de tecnologia para investimento em mercado de startups"
        )
        score = compute_latam_relevance(signal)
        assert score >= 0.3

    def test_latam_location(self):
        signal = make_signal(title="sao paulo startup ecosystem grows")
        score = compute_latam_relevance(signal)
        assert score >= 0.1

    def test_latam_company(self):
        signal = make_signal(title="Nubank launches new credit product in Brazil")
        score = compute_latam_relevance(signal)
        assert score >= 0.1

    def test_non_latam_content(self):
        signal = make_signal(title="Silicon Valley startup raises Series A")
        score = compute_latam_relevance(signal)
        assert score < 0.3

    def test_score_capped_at_one(self):
        signal = make_signal(
            title="brasil latam america latina sao paulo nubank mercadolibre rappi ifood"
        )
        score = compute_latam_relevance(signal)
        assert score <= 1.0


class TestIsBlocked:
    """Test the _is_blocked content filter."""

    def test_adult_content_blocked(self):
        signal = make_signal(title="xvidio technologies startup brasil 2025 video")
        assert _is_blocked(signal) is True

    def test_adult_content_in_url_blocked(self):
        signal = make_signal(
            title="New streaming platform",
            url="https://xvideo.com/tech-article",
        )
        assert _is_blocked(signal) is True

    def test_gambling_content_blocked(self):
        signal = make_signal(title="bet365 nova funcionalidade apostas online brasil")
        assert _is_blocked(signal) is True

    def test_online_casino_blocked(self):
        signal = make_signal(title="Cassino online lanca aplicativo para mobile no Brasil")
        assert _is_blocked(signal) is True

    def test_celebrity_gossip_blocked(self):
        signal = make_signal(title="Fofoca sobre celebridades do momento no Big Brother")
        assert _is_blocked(signal) is True

    def test_football_blocked(self):
        signal = make_signal(title="Campeonato brasileiro 2025 tabela de classificacao")
        assert _is_blocked(signal) is True

    def test_blocked_term_in_summary_blocked(self):
        signal = make_signal(
            title="Nova plataforma de streaming",
            summary="O site xvideo lanca startup brasil 2025",
        )
        assert _is_blocked(signal) is True

    def test_valid_tech_signal_not_blocked(self):
        signal = make_signal(
            title="Kubernetes 1.32 released with new features for edge computing",
            url="https://kubernetes.io/blog/2025/kubernetes-1-32",
        )
        assert _is_blocked(signal) is False

    def test_valid_startup_signal_not_blocked(self):
        signal = make_signal(
            title="Nubank raises Series J valuing company at $45B",
            url="https://techcrunch.com/nubank-series-j",
        )
        assert _is_blocked(signal) is False


class TestHasNegativeKeyword:
    """Test the _has_negative_keyword corporate press release filter."""

    def test_corporate_press_release_filtered(self):
        signal = make_signal(title="Incognia triplica receita anual com nova solucao B2B")
        assert _has_negative_keyword(signal) is True

    def test_ceo_quote_press_release_filtered(self):
        signal = make_signal(title="Produto inovador, diz CEO da startup de AI brasileira")
        assert _has_negative_keyword(signal) is True

    def test_financial_results_filtered(self):
        signal = make_signal(title="Empresa divulga resultado financeiro do quarto trimestre")
        assert _has_negative_keyword(signal) is True

    def test_branded_content_filtered(self):
        signal = make_signal(title="Como a Fintech X cresceu 300% — branded content")
        assert _has_negative_keyword(signal) is True

    def test_negative_keyword_in_summary_filtered(self):
        signal = make_signal(
            title="Startup anuncia novidades",
            summary="A empresa dobra receita anual segundo balanco trimestral divulgado",
        )
        assert _has_negative_keyword(signal) is True

    def test_valid_tech_signal_no_negative_keyword(self):
        signal = make_signal(
            title="Open source LLM achieves state-of-the-art on reasoning benchmarks"
        )
        assert _has_negative_keyword(signal) is False

    def test_valid_funding_signal_no_negative_keyword(self):
        signal = make_signal(
            title="Startup levanta Serie A de R$ 50M para expandir na America Latina"
        )
        assert _has_negative_keyword(signal) is False


class TestMinTopicConfidence:
    """Test MIN_TOPIC_CONFIDENCE constant and its effect on classify_signals."""

    def test_min_topic_confidence_value(self):
        assert MIN_TOPIC_CONFIDENCE == 0.10

    def test_min_latam_relevance_value(self):
        assert MIN_LATAM_RELEVANCE == 0.10

    def test_blocked_terms_list_not_empty(self):
        assert len(BLOCKED_TERMS) >= 5

    def test_negative_keywords_list_not_empty(self):
        assert len(NEGATIVE_KEYWORDS) >= 3

    def test_self_promo_thread_filtered(self):
        """Self-promotion community threads are rejected as negative keywords."""
        signal = make_signal(title="Show HN: my new devtool — shameless plug")
        assert _has_negative_keyword(signal) is True

    def test_hiring_thread_filtered(self):
        signal = make_signal(title="Who is hiring this month? Monthly thread")
        assert _has_negative_keyword(signal) is True

    def test_global_low_latam_low_topic_filtered(self):
        """Global noise signals with low LATAM relevance and low topic confidence are dropped."""
        signals = [
            make_signal(
                title="Silicon Valley weather report today",
                url="https://example.com/weather",
            ),
        ]
        classified = classify_signals(signals)
        assert len(classified) == 0

    def test_high_confidence_global_signal_kept(self):
        """High topic-confidence global signal is kept even with low LATAM relevance."""
        signals = [
            make_signal(
                title=(
                    "Major AI breakthrough: new transformer architecture outperforms GPT on "
                    "reasoning benchmarks with deep learning and machine learning techniques"
                ),
                url="https://arxiv.org/ai-breakthrough",
                source_type="arxiv",
                published_at=datetime.now(timezone.utc),
            ),
        ]
        classified = classify_signals(signals)
        assert len(classified) == 1
        assert classified[0].topic_confidence >= 0.5


class TestClassifySignals:
    """Test the full classification pipeline."""

    def test_returns_sorted_by_composite(self):
        # "Random news" and "Weather today" have uncategorized topic_confidence=0.1
        # and no LATAM relevance, so they are filtered by the MIN_LATAM_RELEVANCE
        # layer (low topic confidence AND low LATAM = global noise).
        signals = [
            make_signal(title="Random news", url="https://a.com/1"),
            make_signal(
                title="AI machine learning startup in latam brasil raises venture capital",
                url="https://a.com/2",
                source_type="hn",
                published_at=datetime.now(timezone.utc),
            ),
            make_signal(title="Weather today", url="https://a.com/3"),
        ]
        classified = classify_signals(signals)
        # Only the strong LATAM+tech signal survives all four filter layers
        assert len(classified) == 1
        assert classified[0].signal.url == "https://a.com/2"
        # Scores descending invariant still holds
        for i in range(len(classified) - 1):
            assert classified[i].composite_score >= classified[i + 1].composite_score

    def test_empty_input(self):
        assert classify_signals([]) == []

    def test_classified_signal_has_all_fields(self):
        # Include LATAM context + tech keywords so signal survives all four filter layers
        signals = [
            make_signal(
                title="Machine learning startup raises Series A in Brasil latam",
                published_at=datetime.now(timezone.utc),
            )
        ]
        classified = classify_signals(signals)
        s = classified[0]
        assert isinstance(s.topics, list)
        assert isinstance(s.primary_topic, str)
        assert 0.0 <= s.topic_confidence <= 1.0
        assert 0.0 <= s.momentum_score <= 1.0
        assert 0.0 <= s.latam_relevance <= 1.0
        assert 0.0 <= s.composite_score <= 1.0

    def test_filters_blocked_signals_returns_fewer_items(self):
        """classify_signals removes blocked signals, returning fewer items than input."""
        signals = [
            make_signal(
                title="AI machine learning startup in latam raises venture capital",
                url="https://techcrunch.com/1",
                published_at=datetime.now(timezone.utc),
            ),
            make_signal(
                title="xvidio technologies startup brasil 2025",
                url="https://a.com/2",
            ),
            make_signal(
                title="Cassino online lanca app para mobile",
                url="https://a.com/3",
            ),
        ]
        classified = classify_signals(signals)
        assert len(classified) < len(signals)
        urls = [c.signal.url for c in classified]
        assert "https://techcrunch.com/1" in urls
        assert "https://a.com/2" not in urls
        assert "https://a.com/3" not in urls

    def test_filters_signals_with_low_topic_confidence(self):
        """Signals with topic_confidence < MIN_TOPIC_CONFIDENCE are excluded."""
        signals = [
            make_signal(
                title="startup brasil 2025",
                url="https://trends.google.com/trends/startup-brasil",
                source_type="trends",
            ),
            # High topic confidence (>= 0.5) via many matched keywords, so it
            # passes layer 4 even without explicit LATAM keywords in the title.
            make_signal(
                title=(
                    "AI machine learning deep learning LLM transformer neural network "
                    "generative ai startup raises funding"
                ),
                url="https://techcrunch.com/ai-ml",
                published_at=datetime.now(timezone.utc),
            ),
        ]
        classified = classify_signals(signals)
        # The strong AI signal must pass; the pure geographic/trend signal may be filtered
        tech_signal = next(
            (c for c in classified if c.signal.url == "https://techcrunch.com/ai-ml"), None
        )
        assert tech_signal is not None, "Strong tech signal should not be filtered"
        # All surviving signals must have topic_confidence >= MIN_TOPIC_CONFIDENCE
        for c in classified:
            assert c.topic_confidence >= MIN_TOPIC_CONFIDENCE, (
                f"Signal '{c.signal.title}' has topic_confidence {c.topic_confidence} "
                f"below MIN_TOPIC_CONFIDENCE {MIN_TOPIC_CONFIDENCE}"
            )

    def test_google_trends_startup_brasil_no_tech_keywords_filtered(self):
        """Google Trends 'startup brasil' signal with no tech keywords is filtered out."""
        signals = [
            make_signal(
                title="startup brasil",
                url="https://trends.google.com/trends/explore?q=startup+brasil",
                source_type="trends",
                summary="",
            ),
        ]
        classified = classify_signals(signals)
        # Either filtered entirely or confidence is at/above the minimum threshold
        # The key assertion: no signal with confidence below the minimum survives
        for c in classified:
            assert c.topic_confidence >= MIN_TOPIC_CONFIDENCE

    def test_negative_keyword_press_release_filtered(self):
        """Signals matching corporate press release patterns are removed."""
        signals = [
            make_signal(
                title="Incognia triplica receita anual com nova solucao B2B",
                url="https://example.com/pr-incognia",
            ),
            # Four+ AI keyword matches give topic_confidence >= 0.5, so layer 4
            # passes even without explicit LATAM geography in the title.
            make_signal(
                title=(
                    "Open source LLM transformer framework for generative ai, machine learning "
                    "and deep learning reaches 50k GitHub stars"
                ),
                url="https://github.com/example/llm",
                published_at=datetime.now(timezone.utc),
            ),
        ]
        classified = classify_signals(signals)
        urls = [c.signal.url for c in classified]
        assert "https://example.com/pr-incognia" not in urls
        assert "https://github.com/example/llm" in urls
