"""Tests for Social Signals persona-based relevance scoring."""

import pytest

from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.social_signals.persona import (
    PERSONAS,
    compute_all_persona_scores,
    compute_persona_relevance,
    get_persona,
    rank_signals_for_persona,
)


def _make_signal(
    text: str = "some text",
    theme: str = "AI",
    likes: int = 0,
    authority_score: float = 0.5,
    handle: str = "user1",
    platform: str = "twitter",
) -> ProcessedSignal:
    """Create a ProcessedSignal with controlled attributes."""
    post = SocialPost(
        text=text,
        url=f"https://example.com/{handle}",
        platform=platform,
        author_handle=handle,
        metrics={"likes": likes},
    )
    return ProcessedSignal(
        post=post,
        theme=theme,
        authority_score=authority_score,
    )


class TestGetPersona:
    def test_valid_keys(self):
        assert get_persona("cto") is not None
        assert get_persona("vc") is not None
        assert get_persona("founder") is not None

    def test_invalid_key(self):
        assert get_persona("invalid") is None

    def test_persona_has_required_fields(self):
        for key in PERSONAS:
            persona = PERSONAS[key]
            assert "label" in persona
            assert "themes_weight" in persona
            assert "keywords_boost" in persona
            assert "voice_types" in persona


class TestComputePersonaRelevance:
    def test_unknown_persona_raises(self):
        signal = _make_signal()
        with pytest.raises(KeyError, match="Unknown persona"):
            compute_persona_relevance(signal, "alien")

    def test_cto_keyword_boost(self):
        """CTO persona should get boosted by infrastructure keywords."""
        signal_infra = _make_signal(text="New infrastructure for scalability and devops")
        signal_plain = _make_signal(text="Some generic news about tech today")

        score_infra = compute_persona_relevance(signal_infra, "cto")
        score_plain = compute_persona_relevance(signal_plain, "cto")

        assert score_infra > score_plain

    def test_vc_keyword_boost(self):
        """VC persona should get boosted by funding keywords."""
        signal_funding = _make_signal(text="Series A funding round for this portfolio company")
        signal_plain = _make_signal(text="Some generic news about tech today")

        score_funding = compute_persona_relevance(signal_funding, "vc")
        score_plain = compute_persona_relevance(signal_plain, "vc")

        assert score_funding > score_plain

    def test_founder_keyword_boost(self):
        """Founder persona should get boosted by growth keywords."""
        signal_growth = _make_signal(text="Product traction and revenue growth are key")
        signal_plain = _make_signal(text="Some generic news about tech today")

        score_growth = compute_persona_relevance(signal_growth, "founder")
        score_plain = compute_persona_relevance(signal_plain, "founder")

        assert score_growth > score_plain

    def test_theme_weight_affects_score(self):
        """CTO values AI more (1.5) than Fintech (0.8)."""
        signal_ai = _make_signal(text="test", theme="AI", likes=20)
        signal_fintech = _make_signal(text="test", theme="Fintech", likes=20)

        score_ai = compute_persona_relevance(signal_ai, "cto")
        score_fintech = compute_persona_relevance(signal_fintech, "cto")

        assert score_ai > score_fintech

    def test_voice_type_boost(self):
        """Matching account type should boost score."""
        signal = _make_signal(text="test", theme="AI")
        score_no_type = compute_persona_relevance(signal, "vc")
        score_with_type = compute_persona_relevance(signal, "vc", account_type="vc")

        assert score_with_type > score_no_type

    def test_score_clamped_to_0_1(self):
        """Score should never exceed 1.0 or go below 0.0."""
        # Lots of keywords + high likes + matching voice type
        signal = _make_signal(
            text="funding series valuation exit portfolio deal round seed ipo acquisition",
            theme="Fintech",
            likes=200,
            authority_score=1.0,
        )
        score = compute_persona_relevance(signal, "vc", account_type="vc")
        assert 0.0 <= score <= 1.0

    def test_authority_score_contributes(self):
        """Higher authority should contribute to persona relevance."""
        signal_low = _make_signal(text="test", authority_score=0.0)
        signal_high = _make_signal(text="test", authority_score=1.0)

        score_low = compute_persona_relevance(signal_low, "cto")
        score_high = compute_persona_relevance(signal_high, "cto")

        assert score_high > score_low

    def test_no_likes_no_metrics_still_works(self):
        """Signal with empty metrics should not crash."""
        post = SocialPost(
            text="infrastructure devops",
            url="https://example.com/1",
            platform="twitter",
            author_handle="user",
            metrics={},
        )
        signal = ProcessedSignal(post=post, theme="AI", authority_score=0.5)
        score = compute_persona_relevance(signal, "cto")
        assert score > 0  # keyword hits should still score


class TestRankSignalsForPersona:
    def test_empty_signals(self):
        result = rank_signals_for_persona([], "cto")
        assert result == []

    def test_ranking_order(self):
        """Signals should be sorted by persona relevance descending."""
        signals = [
            _make_signal(text="generic", handle="low"),
            _make_signal(text="infrastructure scalability architecture", handle="high"),
            _make_signal(text="devops", handle="mid"),
        ]
        ranked = rank_signals_for_persona(signals, "cto")
        handles = [s.post.author_handle for s in ranked]
        # "high" has 3 keyword hits, "mid" has 1, "low" has 0
        assert handles[0] == "high"

    def test_preserves_all_signals(self):
        """Ranking should not drop any signals."""
        signals = [_make_signal(handle=f"user{i}") for i in range(5)]
        ranked = rank_signals_for_persona(signals, "founder")
        assert len(ranked) == 5

    def test_account_types_mapping(self):
        """Should use account_types dict for voice type matching."""
        signals = [
            _make_signal(text="test", handle="vc_person"),
            _make_signal(text="test", handle="random"),
        ]
        ranked = rank_signals_for_persona(
            signals, "vc",
            account_types={"vc_person": "vc"},
        )
        # vc_person should rank higher due to voice type match
        assert ranked[0].post.author_handle == "vc_person"


class TestComputeAllPersonaScores:
    def test_returns_all_personas(self):
        signal = _make_signal()
        scores = compute_all_persona_scores(signal)
        assert set(scores.keys()) == {"cto", "vc", "founder"}

    def test_all_scores_valid_range(self):
        signal = _make_signal(
            text="infrastructure funding product growth",
            likes=50,
            authority_score=0.8,
        )
        scores = compute_all_persona_scores(signal, account_type="founder")
        for key, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score for {key} out of range: {score}"
