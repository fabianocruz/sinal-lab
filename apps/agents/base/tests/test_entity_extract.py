"""Tests for entity name extraction from article titles."""

import pytest

from apps.agents.base.entity_extract import extract_entities


class TestAllCapsExtraction:
    """Heuristic 1: ALL-CAPS words of 3+ characters."""

    def test_single_allcaps_entity(self):
        assert extract_entities("EFEX raises $8M seed round") == ["efex"]

    def test_multiple_allcaps_entities(self):
        result = extract_entities("EFEX e KAVAK fecham rodadas esta semana")
        assert result == ["efex", "kavak"]

    def test_allcaps_in_portuguese(self):
        assert extract_entities("EFEX fecha rodada Pre-Seed") == ["efex"]

    def test_allcaps_with_dollar_amount(self):
        assert extract_entities("VTEX capta US$100M em Serie C") == ["vtex"]

    def test_short_allcaps_ignored(self):
        """2-char ALL-CAPS like AI, ML should be ignored."""
        assert extract_entities("AI and ML trends for 2026") == []

    def test_common_acronyms_ignored(self):
        """Known acronyms (API, CEO, IPO, etc.) are stopwords."""
        assert extract_entities("CEO discusses IPO plans for SaaS company") == []

    def test_currency_codes_ignored(self):
        assert extract_entities("Startup raises USD 5M in BRL equivalent") == []

    def test_region_codes_ignored(self):
        assert extract_entities("LATAM startups grow in EMEA markets") == []


class TestFundingVerbExtraction:
    """Heuristic 2: Capitalized words before funding verbs."""

    def test_raises_pattern(self):
        assert extract_entities("Kavak raises $300M round led by a16z") == ["kavak"]

    def test_fecha_pattern(self):
        assert extract_entities("Stone fecha rodada de investimento") == ["stone"]

    def test_capta_pattern(self):
        assert extract_entities("Creditas capta R$500M para expansao") == ["creditas"]

    def test_closes_pattern(self):
        assert extract_entities("Nubank closes $1B funding round") == ["nubank"]

    def test_secures_pattern(self):
        assert extract_entities("Rappi secures new investment") == ["rappi"]

    def test_multi_word_entity_before_verb(self):
        result = extract_entities("Nu Holdings raises $500M in latest round")
        assert "nu holdings" in result

    def test_common_word_before_verb_ignored(self):
        """Words like 'Startup', 'Company' before verbs are not entities."""
        assert extract_entities("Startup raises $1M in seed round") == []


class TestCombinedHeuristics:
    """Both heuristics applied together."""

    def test_allcaps_plus_verb_deduplicates(self):
        """Same entity found by both heuristics should appear once."""
        result = extract_entities("KAVAK raises $300M from a16z")
        assert result == ["kavak"]

    def test_mixed_entities(self):
        result = extract_entities("EFEX e Sendwave fecham rodadas Pre-Seed")
        assert "efex" in result

    def test_real_headline_latamlist(self):
        result = extract_entities("EFEX raises $8M seed round for logistics tech")
        assert result == ["efex"]

    def test_real_headline_techcrunch(self):
        result = extract_entities(
            "Kavak raises $300M round led by Andreessen Horowitz"
        )
        assert "kavak" in result


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_string(self):
        assert extract_entities("") == []

    def test_whitespace_only(self):
        assert extract_entities("   ") == []

    def test_no_entities(self):
        assert extract_entities("Top 10 programming languages in 2026") == []

    def test_lowercase_title(self):
        assert extract_entities("startup ecosystem grows in brazil") == []

    def test_numbers_not_extracted(self):
        assert extract_entities("Series A worth $50M announced") == []

    def test_returns_lowercase(self):
        result = extract_entities("TOTVS announces new platform")
        assert result == ["totvs"]
        assert all(e == e.lower() for e in result)

    def test_no_duplicates(self):
        result = extract_entities("EFEX: a historia da EFEX no mercado")
        assert result.count("efex") == 1
