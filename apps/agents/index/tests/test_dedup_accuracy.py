"""Cross-source deduplication accuracy tests.

Verifies that the entity matcher + pipeline correctly deduplicates
companies across multiple data sources in realistic scenarios.
"""

import pytest

from apps.agents.sources.entity_matcher import CandidateCompany, DedupIndices
from apps.agents.index.pipeline import run_pipeline


def _candidate(**kwargs) -> CandidateCompany:
    defaults = {"name": "Test", "slug": "test", "source_name": "test", "confidence": 0.5}
    defaults.update(kwargs)
    return CandidateCompany(**defaults)


class TestNubankCrossSource:
    """Nubank appears in 4 sources — should merge when they share identifiers."""

    def test_nubank_four_sources_merge_via_cnpj(self):
        """When all sources share a CNPJ, they merge into 1 company."""
        candidates = [
            # Receita Federal (CNPJ)
            _candidate(
                name="NU PAGAMENTOS S.A.",
                slug="nu-pagamentos-sa",
                cnpj="18236120000158",
                city="SAO PAULO",
                state="SP",
                country="Brasil",
                source_name="receita_federal",
                confidence=0.9,
            ),
            # ABStartups (CNPJ + domain)
            _candidate(
                name="Nubank",
                slug="nubank",
                cnpj="18236120000158",
                website="https://nubank.com.br",
                sector="Fintech",
                city="São Paulo",
                source_name="abstartups",
                confidence=0.7,
            ),
            # YC Portfolio (domain match via running index)
            _candidate(
                name="Nubank",
                slug="nubank",
                website="https://www.nubank.com.br",
                country="Brazil",
                source_name="yc_portfolio",
                confidence=0.85,
            ),
            # Crunchbase (domain match via running index)
            _candidate(
                name="Nubank",
                slug="nubank",
                crunchbase_permalink="nubank",
                website="https://nubank.com.br",
                description="Digital banking platform",
                source_name="crunchbase",
                confidence=0.8,
            ),
        ]

        result = run_pipeline(candidates, DedupIndices())

        # Should merge into exactly 1 company
        assert len(result) == 1
        merged = result[0]

        # Should have all 4 sources
        assert merged.source_count == 4
        assert set(merged.sources) == {"receita_federal", "abstartups", "yc_portfolio", "crunchbase"}

        # Should have the CNPJ from RF
        assert merged.cnpj == "18236120000158"

        # Should have description from Crunchbase
        assert merged.description == "Digital banking platform"

        # Sector from ABStartups
        assert merged.sector == "Fintech"

    def test_rf_without_shared_id_stays_separate(self):
        """RF record with different name and no domain stays separate from domain-linked records."""
        candidates = [
            _candidate(
                name="NU PAGAMENTOS S.A.",
                slug="nu-pagamentos-sa",
                cnpj="18236120000158",
                source_name="receita_federal",
                confidence=0.9,
            ),
            _candidate(
                name="Nubank",
                slug="nubank",
                website="https://nubank.com.br",
                source_name="abstartups",
                confidence=0.7,
            ),
        ]

        result = run_pipeline(candidates, DedupIndices())

        # Without shared CNPJ or domain, name mismatch keeps them separate
        assert len(result) == 2


class TestSameNameDifferentCity:
    """Two companies with the same name but different cities should NOT merge."""

    def test_same_name_different_cities_stay_separate(self):
        candidates = [
            _candidate(
                name="Tech Solutions",
                slug="tech-solutions-sp",
                city="São Paulo",
                source_name="abstartups",
            ),
            _candidate(
                name="Tech Solutions",
                slug="tech-solutions-rj",
                city="Rio de Janeiro",
                source_name="abstartups",
            ),
        ]

        result = run_pipeline(candidates, DedupIndices())

        # Should stay as 2 separate companies
        assert len(result) == 2


class TestFuzzyNameMatch:
    """Similar company names in the same city should merge."""

    def test_fuzzy_match_same_city(self):
        candidates = [
            _candidate(
                name="Stone Pagamentos",
                slug="stone-pagamentos",
                city="São Paulo",
                source_name="rf",
                confidence=0.9,
            ),
            _candidate(
                name="Stone Pagamentos S.A.",
                slug="stone-pagamentos-sa",
                city="São Paulo",
                website="https://stone.co",
                source_name="cb",
                confidence=0.8,
            ),
        ]

        result = run_pipeline(candidates, DedupIndices())

        # Should merge (fuzzy name match > 0.85 + same city)
        assert len(result) == 1
        assert result[0].source_count == 2
        assert result[0].website == "https://stone.co"


class TestExistingDbMatch:
    """Candidates should match against existing DB companies."""

    def test_matches_existing_by_cnpj(self):
        indices = DedupIndices(cnpj_to_slug={"18236120000158": "nubank"})

        candidates = [
            _candidate(
                name="Nu Pagamentos",
                cnpj="18236120000158",
                source_name="rf",
                confidence=0.9,
            ),
        ]

        result = run_pipeline(candidates, indices)
        assert len(result) == 1
        assert result[0].slug == "nubank"
        assert result[0].is_new is False

    def test_matches_existing_by_domain(self):
        indices = DedupIndices(domain_to_slug={"ifood.com.br": "ifood"})

        candidates = [
            _candidate(
                name="iFood",
                website="https://www.ifood.com.br",
                source_name="yc",
            ),
        ]

        result = run_pipeline(candidates, indices)
        assert len(result) == 1
        assert result[0].slug == "ifood"
        assert result[0].is_new is False
