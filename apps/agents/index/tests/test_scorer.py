"""Tests for INDEX scorer."""

import pytest

from apps.agents.index.pipeline import MergedCompany
from apps.agents.index.scorer import (
    _completeness_score,
    _source_count_score,
    score_all,
    score_company,
)


def _merged(**kwargs) -> MergedCompany:
    defaults = {
        "slug": "test-co",
        "name": "Test Co",
        "sources": ["s1"],
        "source_count": 1,
        "best_confidence": 0.5,
    }
    defaults.update(kwargs)
    return MergedCompany(**defaults)


class TestSourceCountScore:
    def test_zero_sources(self):
        assert _source_count_score(0) == 0.1

    def test_one_source(self):
        assert _source_count_score(1) == 0.3

    def test_two_sources(self):
        assert _source_count_score(2) == 0.6

    def test_three_sources(self):
        assert _source_count_score(3) == 0.8

    def test_four_sources(self):
        score = _source_count_score(4)
        assert score > 0.8
        assert score <= 1.0

    def test_monotonically_increasing(self):
        scores = [_source_count_score(i) for i in range(6)]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1]


class TestCompletenessScore:
    def test_empty_company(self):
        merged = _merged()
        score = _completeness_score(merged)
        # Only name and country are filled by default
        assert 0.0 < score < 0.5

    def test_fully_filled_company(self):
        merged = _merged(
            website="https://test.co",
            description="A test company",
            sector="Fintech",
            city="São Paulo",
            cnpj="12345678000199",
            domain="test.co",
            founded_date="2020-01-01",
            team_size=50,
            business_model="SaaS",
            github_url="https://github.com/test",
            linkedin_url="https://linkedin.com/company/test",
            funding_stage="series_a",
            total_funding_usd=10_000_000.0,
        )
        score = _completeness_score(merged)
        assert score == 1.0

    def test_funding_fields_count_toward_completeness(self):
        base = _merged()
        score_base = _completeness_score(base)

        with_funding = _merged(funding_stage="series_a", total_funding_usd=5_000_000.0)
        score_with = _completeness_score(with_funding)

        assert score_with > score_base


class TestScoreCompany:
    def test_basic_score(self):
        merged = _merged()
        score = score_company(merged)
        assert 0.0 < score < 1.0

    def test_rf_boost(self):
        merged_no_rf = _merged(sources=["abstartups"])
        merged_with_rf = _merged(sources=["receita_federal"])

        score_no_rf = score_company(merged_no_rf)
        score_with_rf = score_company(merged_with_rf)

        assert score_with_rf > score_no_rf

    def test_more_sources_higher_score(self):
        merged_1 = _merged(source_count=1, sources=["s1"])
        merged_3 = _merged(source_count=3, sources=["s1", "s2", "s3"])

        assert score_company(merged_3) > score_company(merged_1)

    def test_score_capped_at_1(self):
        merged = _merged(
            source_count=5,
            sources=["receita_federal", "s2", "s3", "s4", "s5"],
            best_confidence=1.0,
            website="https://test.co",
            description="desc",
            sector="Fintech",
            city="SP",
            cnpj="12345678000199",
            domain="test.co",
            founded_date="2020-01-01",
            team_size=50,
            business_model="SaaS",
            github_url="https://github.com/test",
            linkedin_url="https://linkedin.com/company/test",
        )
        score = score_company(merged)
        assert score <= 1.0


class TestScoreAll:
    def test_sorts_descending(self):
        companies = [
            _merged(slug="low", source_count=1, best_confidence=0.3),
            _merged(slug="high", source_count=4, sources=["receita_federal", "s2", "s3", "s4"], best_confidence=0.9),
            _merged(slug="mid", source_count=2, sources=["s1", "s2"], best_confidence=0.6),
        ]
        scored = score_all(companies)
        scores = [s for _, s in scored]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list(self):
        assert score_all([]) == []
