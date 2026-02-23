"""Tests for editorial guidelines module."""

import pytest
from packages.editorial.guidelines import (
    EDITORIAL_TERRITORIES,
    FILTER_CRITERIA,
    FILTER_QUESTION,
    EDITORIAL_RED_FLAGS,
    get_territory_weight,
    get_data_source_agents_for_territory,
    get_territory_keywords,
)


class TestEditorialTerritories:
    """Test suite for EDITORIAL_TERRITORIES constant."""

    def test_all_territories_defined(self):
        """Test that all 4 expected territories are defined."""
        expected_territories = {"ai", "fintech", "engenharia", "venture"}
        assert set(EDITORIAL_TERRITORIES.keys()) == expected_territories

    def test_territory_weights_sum_to_one(self):
        """Test that territory weights sum to 1.0.

        Weights represent relative editorial priorities and should sum
        to exactly 1.0 (0.35 + 0.30 + 0.20 + 0.15).
        """
        total_weight = sum(
            territory["weight"] for territory in EDITORIAL_TERRITORIES.values()
        )
        assert 0.95 <= total_weight <= 1.05

    def test_ai_is_highest_weight(self):
        """Test that AI has the highest editorial weight (35%) — pilar zero."""
        assert EDITORIAL_TERRITORIES["ai"]["weight"] == 0.35
        for key, territory in EDITORIAL_TERRITORIES.items():
            if key != "ai":
                assert territory["weight"] <= 0.35

    def test_all_territories_have_required_fields(self):
        """Test that each territory has all required fields."""
        required_fields = {
            "name", "weight", "data_source_agents", "keywords",
            "filter_questions", "sub_territories"
        }
        for territory_key, territory_data in EDITORIAL_TERRITORIES.items():
            assert set(territory_data.keys()) == required_fields, (
                f"Territory '{territory_key}' missing fields"
            )

    def test_all_territories_have_nonempty_keywords(self):
        """Test that each territory has at least one keyword."""
        for territory_key, territory_data in EDITORIAL_TERRITORIES.items():
            assert len(territory_data["keywords"]) > 0, (
                f"Territory '{territory_key}' has no keywords"
            )

    def test_ai_keywords_include_core_terms(self):
        """Test that AI territory includes expected core keywords."""
        ai_keywords = EDITORIAL_TERRITORIES["ai"]["keywords"]
        core_terms = ["artificial intelligence", "machine learning", "llm", "agentic ai",
                      "generative ai", "mlops", "ai governance"]
        for term in core_terms:
            assert term in ai_keywords, f"AI territory missing keyword '{term}'"

    def test_fintech_keywords_include_core_terms(self):
        """Test that fintech territory includes expected core keywords."""
        fintech_keywords = EDITORIAL_TERRITORIES["fintech"]["keywords"]
        core_terms = ["pix", "open finance", "nubank", "embedded finance"]
        for term in core_terms:
            assert term in fintech_keywords, f"Fintech territory missing keyword '{term}'"

    def test_fintech_absorbed_cripto_keywords(self):
        """Test that fintech territory absorbed stablecoin/tokenização from old cripto territory."""
        fintech_keywords = EDITORIAL_TERRITORIES["fintech"]["keywords"]
        absorbed_terms = ["stablecoin", "tokenização", "drex", "blockchain", "defi"]
        for term in absorbed_terms:
            assert term in fintech_keywords, f"Fintech territory missing absorbed cripto keyword '{term}'"

    def test_venture_absorbed_green_agritech_keywords(self):
        """Test that venture territory absorbed agritech/climate keywords."""
        venture_keywords = EDITORIAL_TERRITORIES["venture"]["keywords"]
        absorbed_terms = ["agritech", "climate tech", "esg", "sustentabilidade", "foodtech"]
        for term in absorbed_terms:
            assert term in venture_keywords, f"Venture territory missing absorbed keyword '{term}'"

    def test_territory_weights_are_valid_probabilities(self):
        """Test that all weights are between 0 and 1."""
        for territory_data in EDITORIAL_TERRITORIES.values():
            weight = territory_data["weight"]
            assert 0.0 <= weight <= 1.0


class TestFilterCriteria:
    """Test suite for FILTER_CRITERIA constant."""

    def test_all_five_criteria_defined(self):
        """Test that all 5 filter criteria are defined."""
        expected_criteria = {
            "has_data", "actionable", "unique", "aligns_territory", "latam_angle"
        }
        assert set(FILTER_CRITERIA.keys()) == expected_criteria

    def test_all_criteria_have_required_fields(self):
        """Test that each criterion has name, description, and weight."""
        required_fields = {"name", "description", "weight"}
        for criterion_data in FILTER_CRITERIA.values():
            assert set(criterion_data.keys()) == required_fields

    def test_criterion_weights_are_positive(self):
        """Test that all criterion weights are positive numbers."""
        for criterion_data in FILTER_CRITERIA.values():
            assert criterion_data["weight"] > 0.0

    def test_has_data_criterion(self):
        """Test that has_data criterion is properly configured."""
        has_data = FILTER_CRITERIA["has_data"]
        assert has_data["name"] == "Tem dados verificáveis"
        assert has_data["weight"] == 1.0
        assert "números" in has_data["description"].lower()

    def test_aligns_territory_mentions_four(self):
        """Test that aligns_territory criterion says '4 territórios'."""
        aligns = FILTER_CRITERIA["aligns_territory"]
        assert "4 territórios" in aligns["name"]

    def test_latam_angle_criterion(self):
        """Test that latam_angle criterion is properly configured."""
        latam_angle = FILTER_CRITERIA["latam_angle"]
        assert latam_angle["name"] == "Tem ângulo LATAM específico"
        assert latam_angle["weight"] == 0.9
        assert "tradução" in latam_angle["description"].lower() or "us" in latam_angle["description"].lower()


class TestFilterQuestion:
    """Test suite for FILTER_QUESTION constant."""

    def test_filter_question_is_nonempty_string(self):
        """Test that filter question is a non-empty string."""
        assert isinstance(FILTER_QUESTION, str)
        assert len(FILTER_QUESTION) > 0

    def test_filter_question_mentions_cto(self):
        """Test that filter question targets CTO persona."""
        assert "cto" in FILTER_QUESTION.lower()

    def test_filter_question_mentions_sao_paulo(self):
        """Test that filter question mentions São Paulo (LATAM context)."""
        assert "são paulo" in FILTER_QUESTION.lower()


class TestEditorialRedFlags:
    """Test suite for EDITORIAL_RED_FLAGS constant."""

    def test_red_flags_is_nonempty_list(self):
        """Test that red flags list is not empty."""
        assert isinstance(EDITORIAL_RED_FLAGS, list)
        assert len(EDITORIAL_RED_FLAGS) > 0

    def test_red_flags_include_expected_items(self):
        """Test that red flags include expected problematic patterns."""
        # Check that key concepts are covered (exact wording may vary)
        flags_text = " ".join(EDITORIAL_RED_FLAGS).lower()
        assert "press release" in flags_text
        assert "hype" in flags_text
        assert "tutorial" in flags_text


class TestGetTerritoryWeight:
    """Test suite for get_territory_weight() function."""

    def test_ai_weight(self):
        """Test getting weight for AI territory (pilar zero)."""
        assert get_territory_weight("ai") == 0.35

    def test_fintech_weight(self):
        """Test getting weight for fintech territory."""
        assert get_territory_weight("fintech") == 0.30

    def test_engenharia_weight(self):
        """Test getting weight for engenharia territory."""
        assert get_territory_weight("engenharia") == 0.20

    def test_venture_weight(self):
        """Test getting weight for venture territory."""
        assert get_territory_weight("venture") == 0.15

    def test_unknown_territory_returns_zero(self):
        """Test that unknown territory returns 0.0."""
        assert get_territory_weight("unknown_territory") == 0.0
        assert get_territory_weight("") == 0.0
        assert get_territory_weight("cripto") == 0.0  # removed in v2


class TestGetDataSourceAgentsForTerritory:
    """Test suite for get_data_source_agents_for_territory() function."""

    def test_ai_data_source_agents(self):
        """Test getting data source agents for AI territory."""
        agents = get_data_source_agents_for_territory("ai")
        assert "RADAR" in agents
        assert "CÓDIGO" in agents

    def test_fintech_data_source_agents(self):
        """Test getting data source agents for fintech territory."""
        agents = get_data_source_agents_for_territory("fintech")
        assert "MERCADO" in agents
        assert "FUNDING" in agents

    def test_engenharia_data_source_agents(self):
        """Test getting data source agents for engenharia territory."""
        agents = get_data_source_agents_for_territory("engenharia")
        assert "CÓDIGO" in agents

    def test_venture_data_source_agents(self):
        """Test getting data source agents for venture territory."""
        agents = get_data_source_agents_for_territory("venture")
        assert "FUNDING" in agents
        assert "INDEX" in agents

    def test_unknown_territory_returns_empty_list(self):
        """Test that unknown territory returns empty list."""
        assert get_data_source_agents_for_territory("unknown") == []
        assert get_data_source_agents_for_territory("") == []


class TestGetTerritoryKeywords:
    """Test suite for get_territory_keywords() function."""

    def test_ai_keywords_nonempty(self):
        """Test that AI keywords list is not empty."""
        keywords = get_territory_keywords("ai")
        assert len(keywords) > 0
        assert "llm" in keywords

    def test_fintech_keywords_include_pix(self):
        """Test that fintech territory includes Pix keyword."""
        keywords = get_territory_keywords("fintech")
        assert "pix" in keywords

    def test_fintech_keywords_include_stablecoin(self):
        """Test that fintech keywords include absorbed stablecoin term."""
        keywords = get_territory_keywords("fintech")
        assert "stablecoin" in keywords

    def test_unknown_territory_returns_empty_list(self):
        """Test that unknown territory returns empty list."""
        assert get_territory_keywords("nonexistent") == []
        assert get_territory_keywords("") == []
