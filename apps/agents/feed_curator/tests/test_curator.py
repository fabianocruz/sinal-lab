"""Tests for Feed Curator core logic — pre-filter, LLM orchestration, and JSON parsing.

Tests for _parse_llm_response use real JSON strings to avoid mocking the parser
itself. Tests for curate_via_llm and load_recent_signals use mocks where necessary.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.agents.feed_curator.curator import (
    CuratedItem,
    _parse_llm_response,
    curate_via_llm,
    pre_filter_spam,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_signal(
    content_hash: str = "abc123",
    platform: str = "twitter",
    author_handle: str = "founder_silva",
    text: str = "Nova rodada seed para fintech brasileira.",
    post_url: str = "https://twitter.com/founder_silva/status/1",
    theme: str = "Fintech",
    sub_theme: str = "seed_rounds",
    published_at: str = "2026-04-01T10:00:00",
    sentiment: float = 0.5,
    authority_score: float = 0.7,
) -> Dict[str, Any]:
    """Create a signal dict with sensible defaults."""
    return {
        "content_hash": content_hash,
        "platform": platform,
        "author_handle": author_handle,
        "text": text,
        "post_url": post_url,
        "theme": theme,
        "sub_theme": sub_theme,
        "published_at": published_at,
        "sentiment": sentiment,
        "authority_score": authority_score,
    }


def make_llm_item(
    content_hash: str = "abc123",
    editorial_headline: str = "Fintech brasileira capta rodada seed",
    editorial_context: str = "Sinal importante para o ecossistema LATAM.",
    relevance_score: int = 85,
    category: str = "Fintech",
) -> Dict[str, Any]:
    """Create a raw LLM output dict with sensible defaults."""
    return {
        "content_hash": content_hash,
        "editorial_headline": editorial_headline,
        "editorial_context": editorial_context,
        "relevance_score": relevance_score,
        "category": category,
    }


# ---------------------------------------------------------------------------
# CuratedItem dataclass
# ---------------------------------------------------------------------------


class TestCuratedItem:
    """Test CuratedItem dataclass construction and field defaults."""

    def test_create_minimal(self):
        item = CuratedItem(
            content_hash="hash001",
            editorial_headline="Startup levanta R$10M",
            editorial_context="Rodada liderada por fundo brasileiro.",
            relevance_score=80,
            category="Startup",
        )
        assert item.content_hash == "hash001"
        assert item.relevance_score == 80
        assert item.category == "Startup"

    def test_defaults_for_optional_fields(self):
        item = CuratedItem(
            content_hash="h",
            editorial_headline="Headline",
            editorial_context="Context",
            relevance_score=50,
            category="AI",
        )
        assert item.source_platform == ""
        assert item.source_url == ""
        assert item.source_author == ""
        assert item.source_text == ""
        assert item.thumbnail_url is None
        assert item.embed_type is None
        assert item.embed_url is None

    def test_create_with_all_fields(self):
        item = CuratedItem(
            content_hash="fullhash",
            editorial_headline="Full Headline",
            editorial_context="Full context sentence.",
            relevance_score=92,
            category="AI",
            source_platform="twitter",
            source_url="https://twitter.com/user/1",
            source_author="user",
            source_text="Original tweet text",
            thumbnail_url="https://img.example.com/thumb.jpg",
            embed_type="youtube",
            embed_url="https://www.youtube.com/embed/abc",
        )
        assert item.source_platform == "twitter"
        assert item.embed_type == "youtube"
        assert item.thumbnail_url == "https://img.example.com/thumb.jpg"


# ---------------------------------------------------------------------------
# pre_filter_spam
# ---------------------------------------------------------------------------


class TestPreFilterSpam:
    """Test spam keyword filtering before LLM call."""

    def test_clean_signal_passes_through(self):
        signals = [make_signal(text="Nubank lança novo produto de crédito.")]
        result = pre_filter_spam(signals)
        assert len(result) == 1

    def test_gambling_signal_removed(self):
        signals = [make_signal(text="Promoção bet365 para apostas esportivas!")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_casino_signal_removed(self):
        signals = [make_signal(text="Cassino online agora disponível no Brasil.")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_sports_bet_english_removed(self):
        signals = [make_signal(text="Try sports bet to win big this weekend!")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_horoscopo_removed(self):
        signals = [make_signal(text="Confira seu horoscopo para hoje.")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_case_insensitive_matching(self):
        # skip_keywords are lowercase; text matching uses .lower()
        signals = [make_signal(text="CASSINO Online ACEITA PIX agora.")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_empty_list_returns_empty(self):
        result = pre_filter_spam([])
        assert result == []

    def test_mixed_batch(self):
        signals = [
            make_signal(content_hash="clean1", text="OpenAI lança novo modelo GPT-5."),
            make_signal(content_hash="spam1", text="Bet365 melhores odds esportivas"),
            make_signal(content_hash="clean2", text="Banco Central publica novo regulamento Pix."),
            make_signal(content_hash="spam2", text="Casino grátis sem depósito"),
        ]
        result = pre_filter_spam(signals)
        hashes = [s["content_hash"] for s in result]
        assert "clean1" in hashes
        assert "clean2" in hashes
        assert "spam1" not in hashes
        assert "spam2" not in hashes

    def test_partial_keyword_match(self):
        # "bet365" is in text even when surrounded by other words
        signals = [make_signal(text="Parceria entre fintechs e bet365 anunciada")]
        result = pre_filter_spam(signals)
        assert len(result) == 0

    def test_missing_text_key_does_not_crash(self):
        signals = [{"content_hash": "x", "platform": "twitter"}]
        result = pre_filter_spam(signals)
        # No text key -> text defaults to "" -> no keyword match -> passes
        assert len(result) == 1

    def test_empty_text_passes_through(self):
        signals = [make_signal(text="")]
        result = pre_filter_spam(signals)
        assert len(result) == 1

    def test_preserves_order(self):
        signals = [
            make_signal(content_hash=f"s{i}", text=f"Signal {i}")
            for i in range(5)
        ]
        result = pre_filter_spam(signals)
        hashes = [s["content_hash"] for s in result]
        assert hashes == ["s0", "s1", "s2", "s3", "s4"]


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    """Test JSON parsing from LLM output — the most critical path."""

    def _signals(self, hashes: List[str] = None) -> List[Dict[str, Any]]:
        if hashes is None:
            hashes = ["abc123"]
        return [make_signal(content_hash=h) for h in hashes]

    # --- Happy path: standard JSON array ---

    def test_parses_json_array(self):
        items = [make_llm_item(content_hash="abc123")]
        raw = json.dumps(items)
        result = _parse_llm_response(raw, self._signals(["abc123"]))
        assert len(result) == 1
        assert result[0].content_hash == "abc123"
        assert result[0].editorial_headline == "Fintech brasileira capta rodada seed"

    def test_parses_multiple_items(self):
        hashes = ["h1", "h2", "h3"]
        items = [make_llm_item(content_hash=h, relevance_score=90 - i * 10) for i, h in enumerate(hashes)]
        raw = json.dumps(items)
        result = _parse_llm_response(raw, self._signals(hashes))
        assert len(result) == 3

    def test_sorted_by_relevance_score_descending(self):
        items = [
            make_llm_item(content_hash="low", relevance_score=30),
            make_llm_item(content_hash="high", relevance_score=90),
            make_llm_item(content_hash="mid", relevance_score=60),
        ]
        raw = json.dumps(items)
        result = _parse_llm_response(raw, self._signals(["low", "high", "mid"]))
        scores = [r.relevance_score for r in result]
        assert scores == sorted(scores, reverse=True)
        assert result[0].content_hash == "high"

    def test_enriches_with_source_metadata(self):
        signals = [make_signal(
            content_hash="abc123",
            platform="twitter",
            author_handle="cto_tech",
            post_url="https://twitter.com/cto_tech/1",
            text="Lançamento de produto incrível para startups.",
        )]
        raw = json.dumps([make_llm_item(content_hash="abc123")])
        result = _parse_llm_response(raw, signals)
        assert result[0].source_platform == "twitter"
        assert result[0].source_author == "cto_tech"
        assert result[0].source_url == "https://twitter.com/cto_tech/1"
        assert "Lançamento de produto" in result[0].source_text

    def test_source_text_truncated_to_200_chars(self):
        long_text = "X" * 500
        signals = [make_signal(content_hash="abc123", text=long_text)]
        raw = json.dumps([make_llm_item(content_hash="abc123")])
        result = _parse_llm_response(raw, signals)
        assert len(result[0].source_text) == 200

    def test_unknown_content_hash_gets_empty_metadata(self):
        # LLM returns a hash not in source_signals
        raw = json.dumps([make_llm_item(content_hash="unknown_hash")])
        result = _parse_llm_response(raw, self._signals(["abc123"]))
        assert len(result) == 1
        assert result[0].source_platform == ""
        assert result[0].source_url == ""

    # --- JSON code fences ---

    def test_strips_json_code_fences(self):
        items = [make_llm_item()]
        raw = f"```json\n{json.dumps(items)}\n```"
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 1

    def test_strips_bare_code_fences(self):
        items = [make_llm_item()]
        raw = f"```\n{json.dumps(items)}\n```"
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 1

    # --- JSONL fallback ---

    def test_parses_jsonl_format(self):
        lines = [
            json.dumps(make_llm_item(content_hash="h1")),
            json.dumps(make_llm_item(content_hash="h2")),
        ]
        raw = "\n".join(lines)
        result = _parse_llm_response(raw, self._signals(["h1", "h2"]))
        assert len(result) == 2

    def test_parses_jsonl_with_blank_lines(self):
        line1 = json.dumps(make_llm_item(content_hash="h1"))
        line2 = json.dumps(make_llm_item(content_hash="h2"))
        raw = f"{line1}\n\n{line2}\n"
        result = _parse_llm_response(raw, self._signals(["h1", "h2"]))
        assert len(result) == 2

    # --- Regex array extraction fallback ---

    def test_extracts_array_from_mixed_text(self):
        items = [make_llm_item(content_hash="abc123")]
        array_str = json.dumps(items)
        raw = f"Aqui estão os itens selecionados:\n{array_str}\n\nEspero que seja útil."
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 1
        assert result[0].content_hash == "abc123"

    def test_extracts_array_with_leading_prose(self):
        items = [make_llm_item(content_hash="abc123", relevance_score=75)]
        raw = "Based on the signals, I selected: " + json.dumps(items)
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 1

    # --- Category validation ---

    def test_valid_category_preserved(self):
        for category in ["AI", "Fintech", "AI in Banking", "Funding", "HealthTech", "DevTools"]:
            raw = json.dumps([make_llm_item(category=category)])
            result = _parse_llm_response(raw, self._signals())
            assert result[0].category == category

    def test_invalid_category_falls_back_to_ai(self):
        raw = json.dumps([make_llm_item(category="Politics")])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].category == "AI"

    def test_empty_category_falls_back_to_ai(self):
        raw = json.dumps([make_llm_item(category="")])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].category == "AI"

    # --- Headline truncation ---

    def test_headline_within_limit_unchanged(self):
        short = "Curta"
        raw = json.dumps([make_llm_item(editorial_headline=short)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].editorial_headline == short

    def test_headline_exactly_at_limit_unchanged(self):
        headline = "A" * 80
        raw = json.dumps([make_llm_item(editorial_headline=headline)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].editorial_headline == headline

    def test_headline_over_limit_truncated_with_ellipsis(self):
        headline = "B" * 100
        raw = json.dumps([make_llm_item(editorial_headline=headline)])
        result = _parse_llm_response(raw, self._signals())
        assert len(result[0].editorial_headline) == 80
        assert result[0].editorial_headline.endswith("...")

    def test_headline_truncation_preserves_max_length(self):
        headline = "C" * 200
        raw = json.dumps([make_llm_item(editorial_headline=headline)])
        result = _parse_llm_response(raw, self._signals())
        assert len(result[0].editorial_headline) <= 80

    # --- Score clamping ---

    def test_score_above_100_clamped_to_100(self):
        raw = json.dumps([make_llm_item(relevance_score=150)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].relevance_score == 100

    def test_score_below_0_clamped_to_0(self):
        raw = json.dumps([make_llm_item(relevance_score=-10)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].relevance_score == 0

    def test_score_at_boundaries(self):
        for score in [0, 100]:
            raw = json.dumps([make_llm_item(relevance_score=score)])
            result = _parse_llm_response(raw, self._signals())
            assert result[0].relevance_score == score

    def test_score_coerced_from_float(self):
        raw = json.dumps([make_llm_item(relevance_score=85.7)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].relevance_score == 85

    # --- Missing required fields ---

    def test_item_missing_content_hash_skipped(self):
        item = {
            "editorial_headline": "Headline",
            "editorial_context": "Context",
            "relevance_score": 80,
            "category": "AI",
        }
        raw = json.dumps([item])
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 0

    def test_item_missing_headline_skipped(self):
        item = {
            "content_hash": "abc123",
            "editorial_context": "Context",
            "relevance_score": 80,
            "category": "AI",
        }
        raw = json.dumps([item])
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 0

    def test_empty_content_hash_skipped(self):
        raw = json.dumps([make_llm_item(content_hash="")])
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 0

    # --- Non-dict items ---

    def test_non_dict_items_in_array_skipped(self):
        raw = json.dumps([
            make_llm_item(content_hash="h1"),
            "not a dict",
            42,
            None,
            make_llm_item(content_hash="h2"),
        ])
        result = _parse_llm_response(raw, self._signals(["h1", "h2"]))
        assert len(result) == 2

    # --- Single object (not array) ---

    def test_single_object_wrapped_in_list(self):
        raw = json.dumps(make_llm_item(content_hash="abc123"))
        result = _parse_llm_response(raw, self._signals())
        assert len(result) == 1

    # --- Empty and invalid inputs ---

    def test_empty_array_returns_empty(self):
        raw = json.dumps([])
        result = _parse_llm_response(raw, self._signals())
        assert result == []

    def test_completely_invalid_json_returns_empty(self):
        result = _parse_llm_response("this is not json at all", self._signals())
        assert result == []

    def test_partial_json_returns_empty(self):
        result = _parse_llm_response('{"content_hash": "abc"', self._signals())
        assert result == []

    def test_empty_string_returns_empty(self):
        result = _parse_llm_response("", self._signals())
        assert result == []

    def test_whitespace_only_returns_empty(self):
        result = _parse_llm_response("   \n\t  ", self._signals())
        assert result == []

    def test_empty_signals_list(self):
        raw = json.dumps([make_llm_item(content_hash="abc123")])
        result = _parse_llm_response(raw, [])
        # Should still parse — just no source metadata
        assert len(result) == 1
        assert result[0].source_platform == ""

    # --- Unicode handling ---

    def test_unicode_in_headline(self):
        headline = "IA generativa revoluciona o setor financeiro no Brasil"
        raw = json.dumps([make_llm_item(editorial_headline=headline)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].editorial_headline == headline

    def test_unicode_in_context(self):
        context = "Mudança significativa para o ecossistema de startups da América Latina."
        raw = json.dumps([make_llm_item(editorial_context=context)])
        result = _parse_llm_response(raw, self._signals())
        assert result[0].editorial_context == context

    def test_ensure_ascii_false_in_source_text(self):
        # Source text with accented characters should survive round-trip
        signals = [make_signal(content_hash="abc123", text="Análise do mercado financeiro brasileiro.")]
        raw = json.dumps([make_llm_item(content_hash="abc123")])
        result = _parse_llm_response(raw, signals)
        assert "Análise" in result[0].source_text


# ---------------------------------------------------------------------------
# curate_via_llm
# ---------------------------------------------------------------------------


class TestCurateViaLlm:
    """Test LLM orchestration for curation."""

    def _make_mock_client(self, response: Optional[str] = None) -> Mock:
        client = Mock()
        client.is_available = response is not None
        client.generate.return_value = response
        return client

    def test_empty_signals_returns_empty(self):
        client = self._make_mock_client()
        result = curate_via_llm([], llm_client=client)
        assert result == []
        client.generate.assert_not_called()

    def test_llm_unavailable_returns_empty(self):
        client = self._make_mock_client(response=None)
        client.is_available = False
        signals = [make_signal()]
        result = curate_via_llm(signals, llm_client=client)
        assert result == []

    def test_llm_returns_empty_string_returns_empty(self):
        client = self._make_mock_client(response="")
        signals = [make_signal()]
        result = curate_via_llm(signals, llm_client=client)
        assert result == []

    def test_llm_returns_valid_json(self):
        items = [make_llm_item(content_hash="abc123")]
        client = self._make_mock_client(response=json.dumps(items))
        signals = [make_signal(content_hash="abc123")]
        result = curate_via_llm(signals, llm_client=client)
        assert len(result) == 1
        assert result[0].content_hash == "abc123"

    def test_generate_called_once(self):
        items = [make_llm_item()]
        client = self._make_mock_client(response=json.dumps(items))
        signals = [make_signal()]
        curate_via_llm(signals, llm_client=client)
        client.generate.assert_called_once()

    def test_output_limit_passed_to_prompt(self):
        items = [make_llm_item()]
        client = self._make_mock_client(response=json.dumps(items))
        signals = [make_signal()]
        curate_via_llm(signals, output_limit=5, llm_client=client)
        call_args = client.generate.call_args
        user_prompt = call_args.kwargs.get("user_prompt") or call_args[1].get("user_prompt") or call_args[0][0]
        assert "5" in user_prompt

    def test_signals_serialized_in_prompt(self):
        client = self._make_mock_client(response=json.dumps([make_llm_item()]))
        signals = [make_signal(content_hash="unique_hash_xyz")]
        curate_via_llm(signals, llm_client=client)
        call_args = client.generate.call_args
        # The signal data must appear somewhere in the call arguments
        all_args = str(call_args)
        assert "unique_hash_xyz" in all_args

    def test_result_sorted_by_relevance_score(self):
        items = [
            make_llm_item(content_hash="low", relevance_score=20),
            make_llm_item(content_hash="high", relevance_score=95),
        ]
        client = self._make_mock_client(response=json.dumps(items))
        signals = [make_signal(content_hash="low"), make_signal(content_hash="high")]
        result = curate_via_llm(signals, llm_client=client)
        assert result[0].relevance_score >= result[-1].relevance_score

    def test_creates_default_llm_client_when_not_provided(self):
        """When no llm_client passed, it creates one. If no API key, returns empty."""
        signals = [make_signal()]
        # Without mocking, LLMClient won't have an API key in test env
        with patch("apps.agents.feed_curator.curator.LLMClient") as MockLLM:
            mock_instance = Mock()
            mock_instance.is_available = False
            MockLLM.return_value = mock_instance
            result = curate_via_llm(signals)
        assert result == []
        MockLLM.assert_called_once()


# ---------------------------------------------------------------------------
# load_recent_signals
# ---------------------------------------------------------------------------


class TestLoadRecentSignals:
    """Test database query for recent signals using SQLite in-memory."""

    @pytest.fixture
    def session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from packages.database.models.base import Base

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()
        yield sess
        sess.close()

    def _add_signal(
        self,
        session,
        content_hash: str,
        theme: str = "AI",
        # load_recent_signals drops bodies shorter than MIN_TEXT_LENGTH (80).
        text: str = (
            "Startup brasileira anuncia rodada de investimento para expandir "
            "sua plataforma de infraestrutura de pagamentos na America Latina."
        ),
        platform: str = "twitter",
        author_handle: str = "user1",
        post_url: str = "https://twitter.com/user/1",
        published_at: Optional[datetime] = None,
    ):
        from packages.database.models.social_signal import SocialSignal
        from uuid import uuid4

        now = published_at or datetime.now(timezone.utc)
        signal = SocialSignal(
            id=uuid4(),
            content_hash=content_hash,
            platform=platform,
            author_handle=author_handle,
            text=text,
            post_url=post_url,
            theme=theme,
            published_at=now,
        )
        session.add(signal)
        session.flush()
        return signal

    def test_returns_signals_with_theme(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        self._add_signal(session, content_hash="h1", theme="AI")
        result = load_recent_signals(session)
        assert len(result) == 1
        assert result[0]["content_hash"] == "h1"

    def test_excludes_signals_without_theme(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals
        from packages.database.models.social_signal import SocialSignal
        from uuid import uuid4

        # Signal with theme
        self._add_signal(session, content_hash="with_theme", theme="Fintech")

        # Signal without theme (NULL)
        no_theme = SocialSignal(
            id=uuid4(),
            content_hash="no_theme",
            platform="twitter",
            post_url="https://twitter.com/user/2",
            theme=None,
            published_at=datetime.now(timezone.utc),
        )
        session.add(no_theme)
        session.flush()

        result = load_recent_signals(session)
        hashes = [r["content_hash"] for r in result]
        assert "with_theme" in hashes
        assert "no_theme" not in hashes

    def test_respects_limit(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        for i in range(10):
            self._add_signal(session, content_hash=f"h{i}", theme="AI")

        result = load_recent_signals(session, limit=3)
        assert len(result) == 3

    def test_returns_empty_when_no_signals(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        result = load_recent_signals(session)
        assert result == []

    def test_returned_dicts_have_required_keys(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        self._add_signal(session, content_hash="h1")
        result = load_recent_signals(session)
        required_keys = {
            "content_hash", "platform", "author_handle", "text",
            "post_url", "theme", "sub_theme", "published_at",
            "sentiment", "authority_score",
        }
        assert required_keys.issubset(set(result[0].keys()))

    def test_text_truncated_to_300_chars(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        long_text = "X" * 500
        self._add_signal(session, content_hash="h1", text=long_text)
        result = load_recent_signals(session)
        assert len(result[0]["text"]) == 300

    def test_none_author_handle_becomes_empty_string(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals
        from packages.database.models.social_signal import SocialSignal
        from uuid import uuid4

        signal = SocialSignal(
            id=uuid4(),
            content_hash="no_author",
            platform="twitter",
            post_url="https://twitter.com/anon/1",
            theme="AI",
            author_handle=None,
            text=(
                "Post anonimo sobre infraestrutura de dados na America Latina "
                "com detalhes suficientes para passar o filtro de tamanho minimo."
            ),
            published_at=datetime.now(timezone.utc),
        )
        session.add(signal)
        session.flush()

        result = load_recent_signals(session)
        match = next(r for r in result if r["content_hash"] == "no_author")
        assert match["author_handle"] == ""

    def test_published_at_serialized_as_isoformat(self, session):
        from apps.agents.feed_curator.curator import load_recent_signals

        ts = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._add_signal(session, content_hash="h1", published_at=ts)
        result = load_recent_signals(session)
        assert "2026-04-01" in result[0]["published_at"]
