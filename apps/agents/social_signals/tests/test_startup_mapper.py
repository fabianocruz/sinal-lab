"""Tests for Social Signals startup mapper."""

import pytest

from apps.agents.social_signals.models import ProcessedSignal, SocialPost
from apps.agents.social_signals.startup_mapper import (
    MIN_COMPANY_NAME_LENGTH,
    _match_company_in_text,
    map_signals_to_startups_static,
)


def _make_signal(
    text: str = "some text",
    theme: str = "AI",
    sentiment: float = 0.5,
    platform: str = "twitter",
    url: str = "https://example.com/1",
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle="user1",
    )
    return ProcessedSignal(post=post, theme=theme, sentiment=sentiment)


class TestMatchCompanyInText:
    def test_exact_word_match(self):
        assert _match_company_in_text("Nubank", "nubank is growing fast") is True

    def test_no_partial_match(self):
        """Should not match partial words."""
        assert _match_company_in_text("Nu", "number of users") is False

    def test_case_insensitive(self):
        assert _match_company_in_text("OpenAI", "openai released a new model") is True

    def test_name_with_spaces(self):
        assert _match_company_in_text("Stone Pagamentos", "stone pagamentos reported earnings") is True

    def test_no_match(self):
        assert _match_company_in_text("Stripe", "paypal is a payment processor") is False


class TestMapSignalsToStartupsStatic:
    def test_empty_signals(self):
        result = map_signals_to_startups_static([], [("Nubank", "nubank")])
        assert result == {}

    def test_empty_companies(self):
        signals = [_make_signal(text="Nubank is great")]
        result = map_signals_to_startups_static(signals, [])
        assert result == {}

    def test_basic_matching(self):
        signals = [
            _make_signal(text="Nubank reported record growth this quarter", sentiment=0.8),
            _make_signal(text="Nubank launches new credit product", sentiment=0.6),
        ]
        companies = [("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)

        assert "nubank" in result
        assert result["nubank"]["signal_count"] == 2
        assert result["nubank"]["name"] == "Nubank"
        assert len(result["nubank"]["signals"]) == 2

    def test_avg_sentiment(self):
        signals = [
            _make_signal(text="Nubank up", sentiment=0.8),
            _make_signal(text="Nubank down", sentiment=0.2),
        ]
        companies = [("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        assert result["nubank"]["avg_sentiment"] == pytest.approx(0.5, abs=0.01)

    def test_themes_collected(self):
        signals = [
            _make_signal(text="Nubank AI", theme="AI"),
            _make_signal(text="Nubank Fintech", theme="Fintech"),
            _make_signal(text="Nubank AI again", theme="AI"),
        ]
        companies = [("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        themes = set(result["nubank"]["themes"])
        assert themes == {"AI", "Fintech"}

    def test_short_names_skipped(self):
        """Company names shorter than min length should be skipped."""
        signals = [_make_signal(text="Nu is a company, AI is everywhere")]
        companies = [("Nu", "nu"), ("AI", "ai"), ("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        assert "nu" not in result
        assert "ai" not in result

    def test_signals_capped_at_five(self):
        signals = [
            _make_signal(text=f"Nubank signal {i}", url=f"https://example.com/{i}")
            for i in range(10)
        ]
        companies = [("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        assert len(result["nubank"]["signals"]) == 5

    def test_sorted_by_signal_count(self):
        signals = [
            _make_signal(text="Stripe is everywhere"),
            _make_signal(text="Nubank is great"),
            _make_signal(text="Nubank launches product"),
        ]
        companies = [("Stripe", "stripe"), ("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        slugs = list(result.keys())
        # Nubank has 2 signals, Stripe has 1
        assert slugs[0] == "nubank"
        assert slugs[1] == "stripe"

    def test_no_match_returns_empty(self):
        signals = [_make_signal(text="Nothing about any company")]
        companies = [("Nubank", "nubank"), ("Stripe", "stripe")]
        result = map_signals_to_startups_static(signals, companies)
        assert result == {}

    def test_custom_min_name_length(self):
        signals = [_make_signal(text="The startup Nu is expanding")]
        companies = [("Nu", "nu")]
        # Default min length (4) should skip "Nu"
        result = map_signals_to_startups_static(signals, companies)
        assert result == {}
        # With lower threshold, should match
        result = map_signals_to_startups_static(signals, companies, min_name_length=2)
        assert "nu" in result

    def test_default_min_length_is_four(self):
        assert MIN_COMPANY_NAME_LENGTH == 4

    def test_signal_text_snippet_truncated(self):
        long_text = "Nubank " + "x" * 200
        signals = [_make_signal(text=long_text)]
        companies = [("Nubank", "nubank")]
        result = map_signals_to_startups_static(signals, companies)
        assert len(result["nubank"]["signals"][0]["text"]) == 150
