"""Tests for confidence scoring module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from apps.agents.base.confidence import ConfidenceScore, compute_confidence


class TestConfidenceScore:
    """Test ConfidenceScore dataclass."""

    def test_create_valid_score(self):
        score = ConfidenceScore(data_quality=0.8, analysis_confidence=0.7)
        assert score.data_quality == 0.8
        assert score.analysis_confidence == 0.7

    def test_composite_calculation(self):
        score = ConfidenceScore(data_quality=0.8, analysis_confidence=0.6)
        # 0.8 * 0.6 + 0.6 * 0.4 = 0.48 + 0.24 = 0.72
        assert score.composite == 0.72

    def test_grade_a(self):
        score = ConfidenceScore(data_quality=0.9, analysis_confidence=0.85)
        assert score.grade == "A"

    def test_grade_b(self):
        score = ConfidenceScore(data_quality=0.7, analysis_confidence=0.65)
        assert score.grade == "B"

    def test_grade_c(self):
        score = ConfidenceScore(data_quality=0.4, analysis_confidence=0.35)
        assert score.grade == "C"

    def test_grade_d(self):
        score = ConfidenceScore(data_quality=0.1, analysis_confidence=0.1)
        assert score.grade == "D"

    def test_display_scale(self):
        score = ConfidenceScore(data_quality=0.8, analysis_confidence=0.6)
        assert score.dq_display == 4.0
        assert score.ac_display == 3.0

    def test_invalid_data_quality_too_high(self):
        with pytest.raises(ValueError, match="data_quality"):
            ConfidenceScore(data_quality=1.5, analysis_confidence=0.5)

    def test_invalid_data_quality_negative(self):
        with pytest.raises(ValueError, match="data_quality"):
            ConfidenceScore(data_quality=-0.1, analysis_confidence=0.5)

    def test_invalid_analysis_confidence(self):
        with pytest.raises(ValueError, match="analysis_confidence"):
            ConfidenceScore(data_quality=0.5, analysis_confidence=1.1)

    def test_to_dict(self):
        score = ConfidenceScore(
            data_quality=0.8,
            analysis_confidence=0.7,
            source_count=3,
            verified=True,
            notes="test",
        )
        d = score.to_dict()
        assert d["data_quality"] == 0.8
        assert d["grade"] == "B"
        assert d["source_count"] == 3
        assert d["verified"] is True
        assert d["notes"] == "test"
        assert "composite" in d
        assert "dq_display" in d
        assert "ac_display" in d

    def test_boundary_scores(self):
        """Test exact boundary values."""
        score_zero = ConfidenceScore(data_quality=0.0, analysis_confidence=0.0)
        assert score_zero.composite == 0.0
        assert score_zero.grade == "D"

        score_one = ConfidenceScore(data_quality=1.0, analysis_confidence=1.0)
        assert score_one.composite == 1.0
        assert score_one.grade == "A"


class TestComputeConfidence:
    """Test the compute_confidence helper."""

    def test_zero_sources(self):
        score = compute_confidence(source_count=0)
        assert score.data_quality == 0.1
        assert score.grade == "D"

    def test_single_source_unverified(self):
        score = compute_confidence(source_count=1, sources_verified=0)
        assert score.data_quality == 0.3
        # Composite: 0.3*0.6 + 0.27*0.4 = 0.288 -> grade D (below 0.3 threshold)
        assert score.grade == "D"

    def test_single_source_verified(self):
        score = compute_confidence(source_count=1, sources_verified=1)
        assert score.data_quality == 0.4

    def test_two_sources_verified(self):
        score = compute_confidence(source_count=2, sources_verified=2)
        assert score.data_quality == 0.65
        assert score.verified is True

    def test_many_sources(self):
        score = compute_confidence(source_count=5, sources_verified=5)
        assert score.data_quality >= 0.7
        assert score.grade in ("A", "B")

    def test_cross_validation_bonus(self):
        without = compute_confidence(source_count=2, sources_verified=2)
        with_cv = compute_confidence(
            source_count=2, sources_verified=2, cross_validated=True
        )
        assert with_cv.data_quality > without.data_quality

    def test_freshness_penalty_stale(self):
        fresh = compute_confidence(source_count=2, data_freshness_days=0)
        stale = compute_confidence(source_count=2, data_freshness_days=100)
        assert stale.data_quality < fresh.data_quality

    def test_freshness_penalty_moderate(self):
        fresh = compute_confidence(source_count=2, data_freshness_days=0)
        moderate = compute_confidence(source_count=2, data_freshness_days=60)
        assert moderate.data_quality < fresh.data_quality
        stale = compute_confidence(source_count=2, data_freshness_days=100)
        assert stale.data_quality < moderate.data_quality
