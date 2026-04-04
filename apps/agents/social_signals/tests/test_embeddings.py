"""Tests for embedding generation — OpenAI client, TF-IDF fallback, and caching."""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.embeddings import (
    EMBEDDING_DIMENSIONS,
    _SKLEARN_AVAILABLE,
    _generate_tfidf_embeddings,
    _prepare_embedding_text,
    clear_embedding_cache,
    generate_embeddings,
    get_embedding_method,
)
from apps.agents.social_signals.models import ProcessedSignal, SocialPost

_requires_sklearn = pytest.mark.skipif(
    not _SKLEARN_AVAILABLE, reason="scikit-learn not installed"
)


def _make_signal(
    text: str = "AI agents for compliance are trending",
    theme: str = "AI",
    sub_theme: str = "AI agents",
    platform: str = "twitter",
    url: str = "https://twitter.com/1",
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=url,
        platform=platform,
        author_handle="testuser",
    )
    return ProcessedSignal(post=post, theme=theme, sub_theme=sub_theme)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear embedding cache before each test."""
    clear_embedding_cache()
    yield
    clear_embedding_cache()


class TestPrepareEmbeddingText:
    """Test text preparation for embedding input."""

    def test_combines_text_theme_subtheme(self):
        signal = _make_signal(text="hello world", theme="AI", sub_theme="agents")
        result = _prepare_embedding_text(signal)
        assert "hello world" in result
        assert "Theme: AI" in result
        assert "Sub-theme: agents" in result

    def test_removes_urls(self):
        signal = _make_signal(text="check https://example.com for more")
        result = _prepare_embedding_text(signal)
        assert "https://example.com" not in result
        assert "check" in result

    def test_removes_mentions_keeps_word(self):
        signal = _make_signal(text="@johndoe said something")
        result = _prepare_embedding_text(signal)
        assert "@johndoe" not in result
        assert "johndoe" in result

    def test_removes_hashtags_keeps_word(self):
        signal = _make_signal(text="#fintech is growing")
        result = _prepare_embedding_text(signal)
        assert "#fintech" not in result
        assert "fintech" in result

    def test_collapses_whitespace(self):
        signal = _make_signal(text="too   many   spaces")
        result = _prepare_embedding_text(signal)
        assert "  " not in result

    def test_truncates_long_text(self):
        long_text = "x" * 10000
        signal = _make_signal(text=long_text)
        result = _prepare_embedding_text(signal)
        assert len(result) <= 8000

    def test_handles_empty_theme(self):
        signal = _make_signal(text="just text", theme="", sub_theme="")
        result = _prepare_embedding_text(signal)
        assert result == "just text"


class TestTfidfFallback:
    """Test TF-IDF embedding generation (no OpenAI)."""

    def test_produces_correct_dimensions(self):
        texts = ["AI agents are transforming banking", "fintech payments infrastructure"]
        embeddings = _generate_tfidf_embeddings(texts)
        assert len(embeddings) == 2
        assert all(len(e) == EMBEDDING_DIMENSIONS for e in embeddings)

    @_requires_sklearn
    def test_different_texts_produce_different_vectors(self):
        texts = [
            "AI is revolutionizing healthcare with machine learning",
            "Bitcoin price reaches new all-time high in crypto markets",
        ]
        embeddings = _generate_tfidf_embeddings(texts)
        # Vectors should not be identical
        assert embeddings[0] != embeddings[1]

    def test_single_text(self):
        embeddings = _generate_tfidf_embeddings(["just one text"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == EMBEDDING_DIMENSIONS

    def test_empty_texts_return_zero_vectors(self):
        embeddings = _generate_tfidf_embeddings(["", ""])
        assert len(embeddings) == 2
        # Should be zero vectors (empty vocabulary)
        assert all(v == 0.0 for v in embeddings[0])

    def test_all_stop_words_return_zero_vectors(self):
        embeddings = _generate_tfidf_embeddings(["the is a an", "it was to be"])
        assert len(embeddings) == 2


class TestGenerateEmbeddings:
    """Test the main generate_embeddings function with caching and fallback."""

    def test_force_tfidf_skips_openai(self):
        signals = [
            _make_signal(text="AI agents for compliance"),
            _make_signal(text="Fintech payments growing", url="https://twitter.com/2"),
        ]
        result = generate_embeddings(signals, force_tfidf=True)
        assert len(result) == 2
        for content_hash, embedding in result.items():
            assert len(embedding) == EMBEDDING_DIMENSIONS

    def test_caching_returns_cached_values(self):
        signal = _make_signal(text="test caching signal")

        # First call generates embeddings
        result1 = generate_embeddings([signal], force_tfidf=True)
        assert signal.content_hash in result1

        # Second call should use cache (even if we change force_tfidf)
        result2 = generate_embeddings([signal], force_tfidf=True)
        assert result2[signal.content_hash] == result1[signal.content_hash]

    def test_mixed_cached_and_uncached(self):
        signal1 = _make_signal(text="cached signal", url="https://twitter.com/1")
        signal2 = _make_signal(text="new signal about banking AI", url="https://twitter.com/2")

        # Cache signal1
        generate_embeddings([signal1], force_tfidf=True)

        # Generate for both (signal1 from cache, signal2 fresh)
        result = generate_embeddings([signal1, signal2], force_tfidf=True)
        assert len(result) == 2
        assert signal1.content_hash in result
        assert signal2.content_hash in result

    def test_empty_signals_returns_empty_dict(self):
        result = generate_embeddings([])
        assert result == {}

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", False)
    def test_falls_back_to_tfidf_when_openai_unavailable(self):
        signals = [_make_signal()]
        result = generate_embeddings(signals)
        assert len(result) == 1
        # Should still produce 1536-dim vectors
        for embedding in result.values():
            assert len(embedding) == EMBEDDING_DIMENSIONS

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", True)
    @patch("apps.agents.social_signals.embeddings._has_openai_key", return_value=True)
    @patch("apps.agents.social_signals.embeddings._call_openai_embeddings")
    def test_uses_openai_when_available(self, mock_openai, mock_key):
        fake_embedding = [0.1] * EMBEDDING_DIMENSIONS
        mock_openai.return_value = [fake_embedding]

        signals = [_make_signal()]
        result = generate_embeddings(signals)

        mock_openai.assert_called_once()
        assert len(result) == 1
        assert list(result.values())[0] == fake_embedding

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", True)
    @patch("apps.agents.social_signals.embeddings._has_openai_key", return_value=True)
    @patch("apps.agents.social_signals.embeddings._call_openai_embeddings", return_value=None)
    def test_falls_back_to_tfidf_on_openai_failure(self, mock_openai, mock_key):
        signals = [_make_signal()]
        result = generate_embeddings(signals)

        # Should still produce results via TF-IDF fallback
        assert len(result) == 1
        for embedding in result.values():
            assert len(embedding) == EMBEDDING_DIMENSIONS


class TestGetEmbeddingMethod:
    """Test embedding method detection."""

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", True)
    @patch("apps.agents.social_signals.embeddings._has_openai_key", return_value=True)
    def test_returns_openai_when_available(self, mock_key):
        assert get_embedding_method() == "openai"

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", False)
    @patch("apps.agents.social_signals.embeddings._SKLEARN_AVAILABLE", True)
    def test_returns_tfidf_when_no_openai(self):
        assert get_embedding_method() == "tfidf"

    @patch("apps.agents.social_signals.embeddings._OPENAI_AVAILABLE", False)
    @patch("apps.agents.social_signals.embeddings._SKLEARN_AVAILABLE", False)
    def test_returns_none_when_nothing_available(self):
        assert get_embedding_method() == "none"
