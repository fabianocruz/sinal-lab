"""Tests for similarity search — cosine similarity, pgvector fallback, JSON fallback."""

import json
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.similarity import (
    _cosine_similarity,
    _find_similar_json_fallback,
    check_pgvector_available,
    find_similar_signals,
    reset_pgvector_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset pgvector cache before each test."""
    reset_pgvector_cache()
    yield
    reset_pgvector_cache()


class TestCosineSimilarity:
    """Test pure-Python cosine similarity computation."""

    def test_identical_vectors(self):
        vec = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(vec, vec) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_different_length_vectors_return_zero(self):
        assert _cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0

    def test_zero_vector_returns_zero(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_empty_vectors_return_zero(self):
        assert _cosine_similarity([], []) == 0.0

    def test_known_similarity(self):
        # cos(45 degrees) ~= 0.7071
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        result = _cosine_similarity(a, b)
        assert abs(result - 0.7071) < 0.001


class TestCheckPgvectorAvailable:
    """Test pgvector availability check."""

    def test_returns_false_when_extension_not_found(self):
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None

        result = check_pgvector_available(session)
        assert result is False

    def test_returns_false_when_extension_exists_but_column_missing(self):
        reset_pgvector_cache()
        session = MagicMock()

        # First call: extension exists
        # Second call: column does not exist
        fetchone_results = [("exists",), None]
        call_count = [0]

        def side_effect():
            result = fetchone_results[call_count[0]]
            call_count[0] += 1
            return result

        mock_result = MagicMock()
        mock_result.fetchone.side_effect = side_effect
        session.execute.return_value = mock_result

        result = check_pgvector_available(session)
        assert result is False

    def test_returns_true_when_both_exist(self):
        reset_pgvector_cache()
        session = MagicMock()

        # Both queries return a row
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("exists",)
        session.execute.return_value = mock_result

        result = check_pgvector_available(session)
        assert result is True

    def test_caches_result(self):
        reset_pgvector_cache()
        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None

        # First call queries DB
        check_pgvector_available(session)
        call_count_1 = session.execute.call_count

        # Second call uses cache
        check_pgvector_available(session)
        assert session.execute.call_count == call_count_1

    def test_handles_db_error_gracefully(self):
        reset_pgvector_cache()
        session = MagicMock()
        session.execute.side_effect = Exception("DB connection failed")

        result = check_pgvector_available(session)
        assert result is False


class TestFindSimilarSignals:
    """Test find_similar_signals with JSON fallback (no pgvector in tests)."""

    def test_empty_embedding_returns_empty(self):
        session = MagicMock()
        result = find_similar_signals(session, [])
        assert result == []

    @patch("apps.agents.social_signals.similarity.check_pgvector_available", return_value=False)
    def test_uses_json_fallback_when_no_pgvector(self, mock_check):
        session = MagicMock()

        # Mock query returning one row with embedding_json
        mock_row = MagicMock()
        mock_row.id = "test-id-1"
        mock_row.content_hash = "abc123"
        mock_row.text = "AI agents for compliance"
        mock_row.theme = "AI"
        mock_row.sub_theme = "AI agents"
        mock_row.platform = "twitter"
        mock_row.published_at = None
        mock_row.embedding_json = [1.0, 0.0, 0.0]  # Simple 3-dim for testing

        session.execute.return_value.fetchall.return_value = [mock_row]

        # Query vector similar to stored
        query_vec = [1.0, 0.0, 0.0]
        results = find_similar_signals(session, query_vec, min_similarity=0.9)

        assert len(results) == 1
        assert results[0]["content_hash"] == "abc123"
        assert results[0]["similarity_score"] >= 0.9

    @patch("apps.agents.social_signals.similarity.check_pgvector_available", return_value=False)
    def test_filters_below_min_similarity(self, mock_check):
        session = MagicMock()

        mock_row = MagicMock()
        mock_row.id = "test-id-1"
        mock_row.content_hash = "abc123"
        mock_row.text = "something"
        mock_row.theme = "AI"
        mock_row.sub_theme = None
        mock_row.platform = "twitter"
        mock_row.published_at = None
        # Orthogonal vector: similarity will be 0
        mock_row.embedding_json = [0.0, 1.0, 0.0]

        session.execute.return_value.fetchall.return_value = [mock_row]

        query_vec = [1.0, 0.0, 0.0]
        results = find_similar_signals(session, query_vec, min_similarity=0.5)

        assert len(results) == 0

    @patch("apps.agents.social_signals.similarity.check_pgvector_available", return_value=False)
    def test_respects_limit(self, mock_check):
        session = MagicMock()

        rows = []
        for i in range(5):
            mock_row = MagicMock()
            mock_row.id = f"test-id-{i}"
            mock_row.content_hash = f"hash{i}"
            mock_row.text = f"signal {i}"
            mock_row.theme = "AI"
            mock_row.sub_theme = None
            mock_row.platform = "twitter"
            mock_row.published_at = None
            mock_row.embedding_json = [1.0, 0.0, 0.0]
            rows.append(mock_row)

        session.execute.return_value.fetchall.return_value = rows

        query_vec = [1.0, 0.0, 0.0]
        results = find_similar_signals(session, query_vec, limit=2, min_similarity=0.9)

        assert len(results) == 2

    @patch("apps.agents.social_signals.similarity.check_pgvector_available", return_value=False)
    def test_handles_invalid_embedding_json_gracefully(self, mock_check):
        session = MagicMock()

        mock_row = MagicMock()
        mock_row.id = "test-id-1"
        mock_row.content_hash = "abc123"
        mock_row.text = "test"
        mock_row.theme = "AI"
        mock_row.sub_theme = None
        mock_row.platform = "twitter"
        mock_row.published_at = None
        mock_row.embedding_json = "not a valid json list"

        session.execute.return_value.fetchall.return_value = [mock_row]

        query_vec = [1.0, 0.0, 0.0]
        # Should not raise, just return empty
        results = find_similar_signals(session, query_vec, min_similarity=0.5)
        assert len(results) == 0

    @patch("apps.agents.social_signals.similarity.check_pgvector_available", return_value=False)
    def test_sorts_by_similarity_descending(self, mock_check):
        session = MagicMock()

        # Row with high similarity
        row_high = MagicMock()
        row_high.id = "id-high"
        row_high.content_hash = "high"
        row_high.text = "high sim"
        row_high.theme = "AI"
        row_high.sub_theme = None
        row_high.platform = "twitter"
        row_high.published_at = None
        row_high.embedding_json = [1.0, 0.0, 0.0]

        # Row with medium similarity
        row_med = MagicMock()
        row_med.id = "id-med"
        row_med.content_hash = "med"
        row_med.text = "med sim"
        row_med.theme = "AI"
        row_med.sub_theme = None
        row_med.platform = "twitter"
        row_med.published_at = None
        row_med.embedding_json = [0.7, 0.7, 0.0]  # ~0.707 similarity to [1,0,0]

        session.execute.return_value.fetchall.return_value = [row_med, row_high]

        query_vec = [1.0, 0.0, 0.0]
        results = find_similar_signals(session, query_vec, min_similarity=0.5)

        assert len(results) == 2
        assert results[0]["content_hash"] == "high"
        assert results[1]["content_hash"] == "med"
        assert results[0]["similarity_score"] > results[1]["similarity_score"]
