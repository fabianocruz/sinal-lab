"""Tests for sector normalization."""

import pytest

from apps.agents.sources.sector_normalizer import (
    SECTOR_OPTIONS,
    SECTOR_ALIASES,
    normalize_sector,
)


class TestNormalizeSector:
    """Tests for normalize_sector()."""

    # --- Canonical values map to themselves ---

    @pytest.mark.parametrize("sector", SECTOR_OPTIONS)
    def test_canonical_maps_to_itself(self, sector):
        assert normalize_sector(sector) == sector

    @pytest.mark.parametrize("sector", SECTOR_OPTIONS)
    def test_canonical_case_insensitive(self, sector):
        assert normalize_sector(sector.lower()) == sector
        assert normalize_sector(sector.upper()) == sector

    # --- Known aliases map correctly ---

    @pytest.mark.parametrize("alias,expected", [
        ("financial services", "Fintech"),
        ("banking", "Fintech"),
        ("payments", "Fintech"),
        ("insurtech", "Fintech"),
        ("ecommerce", "E-commerce"),
        ("retail", "E-commerce"),
        ("marketplace", "E-commerce"),
        ("developer tools", "SaaS"),
        ("b2b", "SaaS"),
        ("healthcare", "Healthtech"),
        ("digital health", "Healthtech"),
        ("education", "Edtech"),
        ("e-learning", "Edtech"),
        ("delivery", "Logistics"),
        ("supply chain", "Logistics"),
        ("agriculture", "Agritech"),
        ("foodtech", "Agritech"),
        ("artificial intelligence", "AI/ML"),
        ("machine learning", "AI/ML"),
        ("real estate", "Proptech"),
        ("construction", "Proptech"),
        ("human resources", "HR Tech"),
        ("recruitment", "HR Tech"),
    ])
    def test_known_aliases(self, alias, expected):
        assert normalize_sector(alias) == expected

    # --- Portuguese aliases ---

    @pytest.mark.parametrize("alias,expected", [
        ("serviços financeiros", "Fintech"),
        ("pagamentos", "Fintech"),
        ("varejo", "E-commerce"),
        ("saúde", "Healthtech"),
        ("educação", "Edtech"),
        ("logística", "Logistics"),
        ("agricultura", "Agritech"),
        ("inteligência artificial", "AI/ML"),
        ("imobiliário", "Proptech"),
        ("recursos humanos", "HR Tech"),
    ])
    def test_portuguese_aliases(self, alias, expected):
        assert normalize_sector(alias) == expected

    # --- Case insensitivity ---

    def test_alias_case_insensitive(self):
        assert normalize_sector("FINTECH") == "Fintech"
        assert normalize_sector("Financial Services") == "Fintech"
        assert normalize_sector("HEALTHCARE") == "Healthtech"

    # --- Substring matching ---

    def test_substring_match_composite(self):
        """Composite sectors like 'Financial Services & Payments' match via substring."""
        assert normalize_sector("Financial Services & Payments") == "Fintech"

    def test_substring_match_verbose(self):
        assert normalize_sector("Digital Health Solutions") == "Healthtech"

    # --- None / empty / unknown ---

    def test_none_returns_none(self):
        assert normalize_sector(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_sector("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_sector("   ") is None

    def test_unknown_sector_returns_none(self):
        assert normalize_sector("Quantum Computing") is None

    def test_gibberish_returns_none(self):
        assert normalize_sector("xyzzy") is None

    # --- Consistency checks ---

    def test_all_aliases_map_to_valid_sectors(self):
        """Every alias value must be a canonical SECTOR_OPTIONS entry."""
        for alias, canonical in SECTOR_ALIASES.items():
            assert canonical in SECTOR_OPTIONS, f"Alias '{alias}' maps to '{canonical}' which is not in SECTOR_OPTIONS"

    def test_sector_options_count(self):
        """Guard against accidental additions/removals."""
        assert len(SECTOR_OPTIONS) == 10
