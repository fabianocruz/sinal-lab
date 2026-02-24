"""Tests for INDEX pipeline — convert, deduplicate, and merge."""

import pytest

from apps.agents.sources.entity_matcher import CandidateCompany, DedupIndices
from apps.agents.index.pipeline import (
    MergedCompany,
    _create_merged,
    _merge_into,
    run_pipeline,
)
from apps.agents.index.converters import (
    convert_all,
    from_abstartups,
    from_receita_federal,
    from_yc,
)


# --- Helper factories ---

def _candidate(**kwargs) -> CandidateCompany:
    defaults = {"name": "Test Co", "slug": "test-co", "source_name": "test", "confidence": 0.5}
    defaults.update(kwargs)
    return CandidateCompany(**defaults)


# --- Converter tests ---

class TestConverters:
    def test_from_receita_federal(self):
        from apps.agents.sources.receita_federal import ReceitaFederalCompany

        rf = ReceitaFederalCompany(
            cnpj="18236120000158",
            razao_social="NU PAGAMENTOS S.A.",
            nome_fantasia="NUBANK",
            cnae_principal="6201500",
            municipio="SAO PAULO",
            uf="SP",
        )
        candidate = from_receita_federal(rf)
        assert candidate.cnpj == "18236120000158"
        assert candidate.name == "NUBANK"
        assert candidate.city == "SAO PAULO"
        assert candidate.source_name == "receita_federal"
        assert candidate.confidence == 0.9

    def test_from_receita_federal_uses_razao_social_when_no_fantasia(self):
        from apps.agents.sources.receita_federal import ReceitaFederalCompany

        rf = ReceitaFederalCompany(
            cnpj="12345678000199",
            razao_social="SOME TECH LTDA",
            cnae_principal="6201500",
        )
        candidate = from_receita_federal(rf)
        assert candidate.name == "SOME TECH LTDA"

    def test_from_abstartups(self):
        from apps.agents.sources.abstartups import ABStartupsCompany

        ab = ABStartupsCompany(
            name="iFood",
            slug="ifood",
            sector="FoodTech",
            city="Campinas",
            website="https://ifood.com.br",
        )
        candidate = from_abstartups(ab)
        assert candidate.name == "iFood"
        assert candidate.domain == "ifood.com.br"
        assert candidate.source_name == "abstartups"
        assert candidate.confidence == 0.7

    def test_from_yc(self):
        from apps.agents.sources.yc_portfolio import YCCompany

        yc = YCCompany(
            name="Neon",
            slug="neon",
            batch="W19",
            vertical="Fintech",
            country="Brazil",
            website="https://neon.com.br",
        )
        candidate = from_yc(yc)
        assert candidate.name == "Neon"
        assert candidate.domain == "neon.com.br"
        assert candidate.source_name == "yc_portfolio"
        assert candidate.confidence == 0.85
        assert "W19" in candidate.tags

    def test_convert_all_combines_sources(self):
        from apps.agents.sources.receita_federal import ReceitaFederalCompany
        from apps.agents.sources.abstartups import ABStartupsCompany

        rf_list = [ReceitaFederalCompany(cnpj="11111111000111", razao_social="Tech A")]
        ab_list = [ABStartupsCompany(name="Startup B", slug="startup-b")]

        result = convert_all(receita_companies=rf_list, abstartups_companies=ab_list)
        assert len(result) == 2
        sources = {c.source_name for c in result}
        assert sources == {"receita_federal", "abstartups"}

    def test_convert_all_handles_none_sources(self):
        result = convert_all()
        assert result == []


# --- Pipeline merge tests ---

class TestMerge:
    def test_create_merged_from_candidate(self):
        c = _candidate(name="Nubank", slug="nubank", website="https://nubank.com.br", confidence=0.9)
        merged = _create_merged(c)
        assert merged.name == "Nubank"
        assert merged.slug == "nubank"
        assert merged.website == "https://nubank.com.br"
        assert merged.source_count == 1

    def test_merge_fills_empty_fields(self):
        merged = MergedCompany(slug="nubank", name="Nubank", sources=["rf"], source_count=1)
        candidate = _candidate(website="https://nubank.com.br", sector="Fintech", source_name="ab")
        _merge_into(merged, candidate)

        assert merged.website == "https://nubank.com.br"
        assert merged.sector == "Fintech"
        assert merged.source_count == 2
        assert "ab" in merged.sources

    def test_merge_does_not_overwrite_existing(self):
        merged = MergedCompany(slug="nubank", name="Nubank", website="https://nubank.com.br", sources=["rf"])
        candidate = _candidate(website="https://other.com", source_name="ab")
        _merge_into(merged, candidate)

        assert merged.website == "https://nubank.com.br"  # Kept original

    def test_merge_deduplicates_tags(self):
        merged = MergedCompany(slug="test", name="Test", tags=["fintech", "ai"], sources=["s1"])
        candidate = _candidate(tags=["ai", "saas"], source_name="s2")
        _merge_into(merged, candidate)

        assert sorted(merged.tags) == ["ai", "fintech", "saas"]

    def test_merge_updates_confidence(self):
        merged = MergedCompany(slug="test", name="Test", best_confidence=0.5, sources=["s1"])
        candidate = _candidate(confidence=0.9, source_name="s2")
        _merge_into(merged, candidate)
        assert merged.best_confidence == 0.9

    def test_merge_total_funding_takes_max(self):
        merged = _create_merged(_candidate(total_funding_usd=1_000_000.0, source_name="s1"))
        candidate2 = _candidate(total_funding_usd=5_000_000.0, source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.total_funding_usd == 5_000_000.0

    def test_merge_total_funding_none_does_not_overwrite(self):
        merged = _create_merged(_candidate(total_funding_usd=2_000_000.0, source_name="s1"))
        candidate2 = _candidate(total_funding_usd=None, source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.total_funding_usd == 2_000_000.0

    def test_merge_total_funding_lower_does_not_overwrite(self):
        merged = _create_merged(_candidate(total_funding_usd=5_000_000.0, source_name="s1"))
        candidate2 = _candidate(total_funding_usd=1_000_000.0, source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.total_funding_usd == 5_000_000.0

    def test_merge_funding_stage_takes_highest(self):
        merged = _create_merged(_candidate(funding_stage="seed", source_name="s1"))
        candidate2 = _candidate(funding_stage="series_b", source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.funding_stage == "series_b"

    def test_merge_funding_stage_does_not_downgrade(self):
        merged = _create_merged(_candidate(funding_stage="series_c", source_name="s1"))
        candidate2 = _candidate(funding_stage="seed", source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.funding_stage == "series_c"

    def test_merge_funding_stage_none_does_not_overwrite(self):
        merged = _create_merged(_candidate(funding_stage="series_a", source_name="s1"))
        candidate2 = _candidate(funding_stage=None, source_name="s2")
        _merge_into(merged, candidate2)
        assert merged.funding_stage == "series_a"

    def test_create_merged_carries_funding_fields(self):
        c = _candidate(funding_stage="seed", total_funding_usd=500_000.0)
        merged = _create_merged(c)
        assert merged.funding_stage == "seed"
        assert merged.total_funding_usd == 500_000.0


# --- Full pipeline tests ---

class TestRunPipeline:
    def test_new_companies_are_created(self):
        candidates = [
            _candidate(name="Alpha", slug="alpha", source_name="s1"),
            _candidate(name="Beta", slug="beta", source_name="s1"),
        ]
        result = run_pipeline(candidates, DedupIndices())
        assert len(result) == 2
        assert all(m.is_new for m in result)

    def test_same_cnpj_merges(self):
        candidates = [
            _candidate(name="Nubank", slug="nubank", cnpj="18236120000158", source_name="rf", confidence=0.9),
            _candidate(name="Nu Pagamentos", cnpj="18236120000158", source_name="cb", confidence=0.8, website="https://nubank.com.br"),
        ]
        result = run_pipeline(candidates, DedupIndices())
        assert len(result) == 1
        assert result[0].source_count == 2
        assert result[0].website == "https://nubank.com.br"

    def test_existing_db_match_not_new(self):
        indices = DedupIndices(cnpj_to_slug={"11111111000111": "existing-co"})
        candidates = [_candidate(name="Existing Co", cnpj="11111111000111", source_name="rf")]
        result = run_pipeline(candidates, indices)
        assert len(result) == 1
        assert result[0].is_new is False

    def test_empty_candidates(self):
        result = run_pipeline([], DedupIndices())
        assert result == []

    def test_domain_dedup_within_batch(self):
        candidates = [
            _candidate(name="iFood", slug="ifood", website="https://ifood.com.br", source_name="yc"),
            _candidate(name="iFood Delivery", website="https://www.ifood.com.br", source_name="ab"),
        ]
        result = run_pipeline(candidates, DedupIndices())
        assert len(result) == 1
        assert result[0].source_count == 2
