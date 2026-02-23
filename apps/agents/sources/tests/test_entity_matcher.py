"""Tests for cross-source entity matcher."""

import pytest

from apps.agents.sources.entity_matcher import (
    CandidateCompany,
    DedupIndices,
    MatchResult,
    _name_city_key,
    _name_similarity,
    match_batch,
    match_single,
    normalize_cnpj,
    normalize_domain,
)


# --- normalize_domain tests ---


class TestNormalizeDomain:
    def test_strips_protocol_and_www(self):
        assert normalize_domain("https://www.nubank.com.br") == "nubank.com.br"

    def test_strips_path_and_query(self):
        assert normalize_domain("https://stone.co/about?ref=1") == "stone.co"

    def test_adds_scheme_if_missing(self):
        assert normalize_domain("ifood.com.br") == "ifood.com.br"

    def test_returns_none_for_empty(self):
        assert normalize_domain(None) is None
        assert normalize_domain("") is None
        assert normalize_domain("   ") is None

    def test_lowercases(self):
        assert normalize_domain("HTTP://WWW.Nubank.COM.BR") == "nubank.com.br"


# --- normalize_cnpj tests ---


class TestNormalizeCnpj:
    def test_strips_formatting(self):
        assert normalize_cnpj("18.236.120/0001-58") == "18236120000158"

    def test_already_clean(self):
        assert normalize_cnpj("18236120000158") == "18236120000158"

    def test_returns_none_for_wrong_length(self):
        assert normalize_cnpj("123") is None
        assert normalize_cnpj("1234567890123456") is None

    def test_returns_none_for_empty(self):
        assert normalize_cnpj(None) is None
        assert normalize_cnpj("") is None


# --- _name_similarity tests ---


class TestNameSimilarity:
    def test_identical_names(self):
        assert _name_similarity("Nubank", "Nubank") == 1.0

    def test_case_insensitive(self):
        assert _name_similarity("Nubank", "nubank") == 1.0

    def test_similar_names(self):
        score = _name_similarity("Stone Pagamentos", "Stone Payments")
        assert score > 0.6

    def test_different_names(self):
        score = _name_similarity("Nubank", "iFood")
        assert score < 0.3

    def test_empty_returns_zero(self):
        assert _name_similarity("", "test") == 0.0
        assert _name_similarity("test", "") == 0.0


# --- match_single tests ---


class TestMatchSingle:
    def _make_indices(self, **kwargs) -> DedupIndices:
        return DedupIndices(**kwargs)

    def test_cnpj_exact_match(self):
        indices = self._make_indices(cnpj_to_slug={"18236120000158": "nubank"})
        candidate = CandidateCompany(name="Nu Pagamentos", cnpj="18.236.120/0001-58")
        result = match_single(candidate, indices)
        assert result.matched_slug == "nubank"
        assert result.match_type == "cnpj"
        assert result.match_confidence == 1.0
        assert result.is_new is False

    def test_domain_exact_match(self):
        indices = self._make_indices(domain_to_slug={"nubank.com.br": "nubank"})
        candidate = CandidateCompany(name="Nubank", website="https://www.nubank.com.br")
        result = match_single(candidate, indices)
        assert result.matched_slug == "nubank"
        assert result.match_type == "domain"
        assert result.match_confidence == 0.95

    def test_permalink_match(self):
        indices = self._make_indices(permalink_to_slug={"nubank": "nubank"})
        candidate = CandidateCompany(name="Nubank", crunchbase_permalink="nubank")
        result = match_single(candidate, indices)
        assert result.matched_slug == "nubank"
        assert result.match_type == "permalink"
        assert result.match_confidence == 0.9

    def test_fuzzy_name_match_same_city(self):
        indices = self._make_indices(
            name_city_to_slug={"stone pagamentos|são paulo": "stone-pagamentos"}
        )
        candidate = CandidateCompany(name="Stone Pagamentos S.A.", city="São Paulo")
        result = match_single(candidate, indices)
        assert result.matched_slug == "stone-pagamentos"
        assert result.match_type == "fuzzy_name"
        assert result.is_new is False

    def test_fuzzy_name_different_city_no_match(self):
        indices = self._make_indices(
            name_city_to_slug={"stone pagamentos|são paulo": "stone-pagamentos"}
        )
        candidate = CandidateCompany(name="Stone Pagamentos", city="Rio de Janeiro")
        result = match_single(candidate, indices)
        assert result.is_new is True

    def test_no_match_returns_new(self):
        indices = self._make_indices()
        candidate = CandidateCompany(name="Totally New Company", city="Lima")
        result = match_single(candidate, indices)
        assert result.is_new is True
        assert result.match_type == "new"
        assert result.match_confidence == 0.0

    def test_cnpj_takes_priority_over_domain(self):
        """CNPJ match should win even if domain also matches a different slug."""
        indices = self._make_indices(
            cnpj_to_slug={"18236120000158": "nubank"},
            domain_to_slug={"nubank.com.br": "some-other-slug"},
        )
        candidate = CandidateCompany(
            name="Nubank", cnpj="18236120000158", website="https://nubank.com.br"
        )
        result = match_single(candidate, indices)
        assert result.matched_slug == "nubank"
        assert result.match_type == "cnpj"


# --- match_batch tests ---


class TestMatchBatch:
    def test_intra_batch_dedup_by_cnpj(self):
        """Second occurrence of same CNPJ should match first in batch."""
        indices = DedupIndices()
        candidates = [
            CandidateCompany(
                name="Nubank", slug="nubank", cnpj="18236120000158", source_name="rf"
            ),
            CandidateCompany(
                name="Nu Pagamentos", cnpj="18236120000158", source_name="cb"
            ),
        ]
        results = match_batch(candidates, indices)
        assert results[0][1].is_new is True  # First is new
        assert results[1][1].is_new is False  # Second matches first
        assert results[1][1].match_type == "cnpj"

    def test_intra_batch_dedup_by_domain(self):
        indices = DedupIndices()
        candidates = [
            CandidateCompany(
                name="iFood",
                slug="ifood",
                website="https://ifood.com.br",
                source_name="yc",
            ),
            CandidateCompany(
                name="iFood Delivery",
                website="https://www.ifood.com.br",
                source_name="ab",
            ),
        ]
        results = match_batch(candidates, indices)
        assert results[0][1].is_new is True
        assert results[1][1].is_new is False
        assert results[1][1].match_type == "domain"

    def test_existing_db_match(self):
        indices = DedupIndices(cnpj_to_slug={"11111111000111": "existing-co"})
        candidates = [
            CandidateCompany(name="Existing Co", cnpj="11111111000111"),
        ]
        results = match_batch(candidates, indices)
        assert results[0][1].is_new is False
        assert results[0][1].matched_slug == "existing-co"

    def test_empty_batch(self):
        results = match_batch([], DedupIndices())
        assert results == []

    def test_does_not_mutate_original_indices(self):
        indices = DedupIndices()
        candidates = [CandidateCompany(name="New Co", slug="new-co", cnpj="12345678000199")]
        match_batch(candidates, indices)
        assert len(indices.cnpj_to_slug) == 0  # Original unchanged
