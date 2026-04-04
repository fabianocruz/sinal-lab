"""Tests for embedding-based clustering and centroid computation."""

from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.clusterer import (
    _compute_cosine_distance_matrix,
    cluster_signals_with_embeddings,
    compute_cluster_centroid,
)
from apps.agents.social_signals.models import ProcessedSignal, SocialPost


def _make_signal(
    text: str = "test post",
    theme: str = "AI",
    sub_theme: str = "",
    url: str = "https://twitter.com/1",
) -> ProcessedSignal:
    post = SocialPost(
        text=text,
        url=url,
        platform="twitter",
        author_handle="testuser",
    )
    return ProcessedSignal(post=post, theme=theme, sub_theme=sub_theme)


class TestComputeCosineDistanceMatrix:
    """Test pairwise cosine distance matrix computation."""

    def test_identical_vectors_have_zero_distance(self):
        embeddings = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        matrix = _compute_cosine_distance_matrix(embeddings)
        assert abs(matrix[0][1]) < 1e-6
        assert abs(matrix[1][0]) < 1e-6

    def test_orthogonal_vectors_have_distance_one(self):
        embeddings = [[1.0, 0.0], [0.0, 1.0]]
        matrix = _compute_cosine_distance_matrix(embeddings)
        assert abs(matrix[0][1] - 1.0) < 1e-6

    def test_diagonal_is_zero(self):
        embeddings = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        matrix = _compute_cosine_distance_matrix(embeddings)
        for i in range(3):
            assert matrix[i][i] == 0.0

    def test_symmetry(self):
        embeddings = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        matrix = _compute_cosine_distance_matrix(embeddings)
        for i in range(3):
            for j in range(3):
                assert abs(matrix[i][j] - matrix[j][i]) < 1e-6

    def test_single_vector(self):
        matrix = _compute_cosine_distance_matrix([[1.0, 2.0]])
        assert matrix == [[0.0]]


class TestComputeClusterCentroid:
    """Test centroid computation for signal clusters."""

    def test_single_signal_centroid_equals_embedding(self):
        signal = _make_signal()
        embedding = [1.0, 2.0, 3.0]
        embeddings = {signal.content_hash: embedding}

        centroid = compute_cluster_centroid([signal], embeddings)
        assert centroid == [1.0, 2.0, 3.0]

    def test_two_signals_centroid_is_mean(self):
        s1 = _make_signal(url="https://twitter.com/1")
        s2 = _make_signal(url="https://twitter.com/2")

        embeddings = {
            s1.content_hash: [2.0, 4.0],
            s2.content_hash: [6.0, 8.0],
        }

        centroid = compute_cluster_centroid([s1, s2], embeddings)
        assert centroid == [4.0, 6.0]

    def test_missing_embeddings_are_skipped(self):
        s1 = _make_signal(url="https://twitter.com/1")
        s2 = _make_signal(url="https://twitter.com/2")

        # Only s1 has an embedding
        embeddings = {s1.content_hash: [3.0, 6.0]}

        centroid = compute_cluster_centroid([s1, s2], embeddings)
        assert centroid == [3.0, 6.0]

    def test_no_embeddings_returns_none(self):
        signal = _make_signal()
        centroid = compute_cluster_centroid([signal], {})
        assert centroid is None

    def test_empty_signals_returns_none(self):
        centroid = compute_cluster_centroid([], {"hash": [1.0, 2.0]})
        assert centroid is None


class TestClusterSignalsWithEmbeddings:
    """Test the embedding-based clustering entry point."""

    def test_empty_signals_returns_empty(self):
        result = cluster_signals_with_embeddings([], {})
        assert result == []

    def test_no_embeddings_falls_back_to_tfidf(self):
        signals = [
            _make_signal(text="AI agents in compliance", url="https://twitter.com/1"),
            _make_signal(text="AI compliance automation", url="https://twitter.com/2"),
            _make_signal(text="AI agents banking sector", url="https://twitter.com/3"),
        ]

        result = cluster_signals_with_embeddings(signals, {})
        # Should produce some clusters via TF-IDF fallback
        assert len(result) >= 1
        total_signals = sum(c.signal_count for c in result)
        assert total_signals == 3

    def test_low_coverage_falls_back_to_tfidf(self):
        signals = [
            _make_signal(text="AI agents trending", url=f"https://twitter.com/{i}")
            for i in range(10)
        ]

        # Only 2 out of 10 have embeddings (20% < 50% threshold)
        embeddings = {
            signals[0].content_hash: [1.0] * 10,
            signals[1].content_hash: [0.9] * 10,
        }

        result = cluster_signals_with_embeddings(signals, embeddings)
        # Should have produced clusters (via fallback)
        assert len(result) >= 1

    def test_with_sufficient_embeddings_clusters_signals(self):
        # Create signals with distinct topics
        ai_signals = [
            _make_signal(text="Machine learning revolutionizes healthcare", theme="AI", url="https://twitter.com/1"),
            _make_signal(text="Deep learning for medical imaging", theme="AI", url="https://twitter.com/2"),
            _make_signal(text="Neural networks in drug discovery", theme="AI", url="https://twitter.com/3"),
        ]
        fintech_signals = [
            _make_signal(text="Digital payments in Latin America", theme="Fintech", url="https://twitter.com/4"),
            _make_signal(text="Mobile payments grow in Brazil", theme="Fintech", url="https://twitter.com/5"),
            _make_signal(text="Payment infrastructure modernization", theme="Fintech", url="https://twitter.com/6"),
        ]

        all_signals = ai_signals + fintech_signals

        # Create embeddings that put AI and Fintech in different directions
        embeddings = {}
        for s in ai_signals:
            embeddings[s.content_hash] = [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        for s in fintech_signals:
            embeddings[s.content_hash] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9, 0.1]

        result = cluster_signals_with_embeddings(
            all_signals, embeddings,
            distance_threshold=0.5,
            min_cluster_size=2,
        )

        assert len(result) >= 2
        total_signals = sum(c.signal_count for c in result)
        assert total_signals == 6

    def test_handles_clustering_exception_gracefully(self):
        signals = [
            _make_signal(text="test signal", url=f"https://twitter.com/{i}")
            for i in range(5)
        ]
        embeddings = {s.content_hash: [1.0] * 10 for s in signals}

        # Patch sklearn clustering to raise
        with patch(
            "apps.agents.social_signals.clusterer._cluster_with_embeddings",
            side_effect=RuntimeError("sklearn exploded"),
        ):
            result = cluster_signals_with_embeddings(signals, embeddings)
            # Should fall back to TF-IDF and still produce results
            assert len(result) >= 1

    def test_sorted_by_signal_count_descending(self):
        signals = [
            _make_signal(text="topic A signal 1", theme="AI", url="https://twitter.com/1"),
            _make_signal(text="topic A signal 2", theme="AI", url="https://twitter.com/2"),
            _make_signal(text="topic A signal 3", theme="AI", url="https://twitter.com/3"),
            _make_signal(text="topic B signal 1", theme="Fintech", url="https://twitter.com/4"),
            _make_signal(text="topic B signal 2", theme="Fintech", url="https://twitter.com/5"),
        ]

        # Group by similarity
        embeddings = {}
        for s in signals[:3]:
            embeddings[s.content_hash] = [1.0, 0.0]
        for s in signals[3:]:
            embeddings[s.content_hash] = [0.0, 1.0]

        result = cluster_signals_with_embeddings(
            signals, embeddings, distance_threshold=0.5, min_cluster_size=1,
        )

        for i in range(len(result) - 1):
            assert result[i].signal_count >= result[i + 1].signal_count
