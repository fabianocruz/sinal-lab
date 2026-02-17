"""Tests for editorial guidelines module."""

import pytest
from packages.editorial.guidelines import (
    EDITORIAL_TERRITORIES,
    FILTER_CRITERIA,
    FILTER_QUESTION,
    EDITORIAL_RED_FLAGS,
    get_territory_weight,
    get_primary_agents_for_territory,
    get_territory_keywords,
)


class TestEditorialTerritories:
    """Test suite for EDITORIAL_TERRITORIES constant."""

    def test_all_territories_defined(self):
        """Test that all 6 expected territories are defined."""
        expected_territories = {
            "fintech", "ai", "cripto", "engenharia", "venture", "green_agritech"
        }
        assert set(EDITORIAL_TERRITORIES.keys()) == expected_territories

    def test_territory_weights_sum_to_one(self):
        """Test that territory weights sum to approximately 1.0."""
        total_weight = sum(
            territory["weight"] for territory in EDITORIAL_TERRITORIES.values()
        )
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error

    def test_fintech_is_highest_weight(self):
        """Test that fintech has the highest editorial weight (40%)."""
        assert EDITORIAL_TERRITORIES["fintech"]["weight"] == 0.40
        for key, territory in EDITORIAL_TERRITORIES.items():
            if key != "fintech":
                assert territory["weight"] <= 0.40

    def test_all_territories_have_required_fields(self):
        """Test that each territory has all required fields."""
        required_fields = {
            "name", "weight", "primary_agents", "keywords",
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

    def test_fintech_keywords_include_core_terms(self):
        """Test that fintech territory includes expected core keywords."""
        fintech_keywords = EDITORIAL_TERRITORIES["fintech"]["keywords"]
        core_terms = ["pix", "open finance", "nubank", "embedded finance"]
        for term in core_terms:
            assert term in fintech_keywords

    def test_ai_keywords_include_core_terms(self):
        """Test that AI territory includes expected core keywords."""
        ai_keywords = EDITORIAL_TERRITORIES["ai"]["keywords"]
        core_terms = ["artificial intelligence", "machine learning", "llm", "agentic ai"]
        for term in core_terms:
            assert term in ai_keywords

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
        expected_flags = [
            "press release sem análise",
            "hype sem substância",
            "tutorial básico",
        ]
        for flag in expected_flags:
            assert flag in EDITORIAL_RED_FLAGS


class TestGetTerritoryWeight:
    """Test suite for get_territory_weight() function."""

    def test_fintech_weight(self):
        """Test getting weight for fintech territory."""
        assert get_territory_weight("fintech") == 0.40

    def test_ai_weight(self):
        """Test getting weight for AI territory."""
        assert get_territory_weight("ai") == 0.20

    def test_unknown_territory_returns_zero(self):
        """Test that unknown territory returns 0.0."""
        assert get_territory_weight("unknown_territory") == 0.0
        assert get_territory_weight("") == 0.0
        assert get_territory_weight("xyz123") == 0.0


class TestGetPrimaryAgentsForTerritory:
    """Test suite for get_primary_agents_for_territory() function."""

    def test_fintech_primary_agents(self):
        """Test getting primary agents for fintech territory."""
        agents = get_primary_agents_for_territory("fintech")
        assert "MERCADO" in agents
        assert "FUNDING" in agents

    def test_ai_primary_agents(self):
        """Test getting primary agents for AI territory."""
        agents = get_primary_agents_for_territory("ai")
        assert "RADAR" in agents
        assert "CÓDIGO" in agents

    def test_engenharia_primary_agents(self):
        """Test getting primary agents for engenharia territory."""
        agents = get_primary_agents_for_territory("engenharia")
        assert "CÓDIGO" in agents

    def test_unknown_territory_returns_empty_list(self):
        """Test that unknown territory returns empty list."""
        assert get_primary_agents_for_territory("unknown") == []
        assert get_primary_agents_for_territory("") == []


class TestGetTerritoryKeywords:
    """Test suite for get_territory_keywords() function."""

    def test_fintech_keywords_nonempty(self):
        """Test that fintech keywords list is not empty."""
        keywords = get_territory_keywords("fintech")
        assert len(keywords) > 0
        assert "pix" in keywords

    def test_cripto_keywords_include_stablecoin(self):
        """Test that cripto territory includes stablecoin keywords."""
        keywords = get_territory_keywords("cripto")
        assert "stablecoin" in keywords
        assert "drex" in keywords

    def test_unknown_territory_returns_empty_list(self):
        """Test that unknown territory returns empty list."""
        assert get_territory_keywords("nonexistent") == []
        assert get_territory_keywords("") == []
