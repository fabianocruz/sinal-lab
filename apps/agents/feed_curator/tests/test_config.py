"""Tests for Feed Curator configuration — defaults, prompts, and validation."""

from apps.agents.feed_curator.config import (
    CURATOR_SYSTEM_PROMPT,
    CURATOR_USER_PROMPT_TEMPLATE,
    FEED_CURATOR_CONFIG,
    FeedCuratorConfig,
)


class TestFeedCuratorConfigDefaults:
    """Verify default configuration values are sensible."""

    def test_version_is_set(self):
        assert FEED_CURATOR_CONFIG.version == "0.1.0"

    def test_persona_name(self):
        assert FEED_CURATOR_CONFIG.persona_name == "Ana Torres"

    def test_schedule_hours_positive(self):
        assert FEED_CURATOR_CONFIG.schedule_hours > 0

    def test_default_input_limit_positive(self):
        assert FEED_CURATOR_CONFIG.default_input_limit > 0

    def test_default_output_limit_positive(self):
        assert FEED_CURATOR_CONFIG.default_output_limit > 0

    def test_output_limit_less_than_input_limit(self):
        # Output must be a subset of input
        assert FEED_CURATOR_CONFIG.default_output_limit < FEED_CURATOR_CONFIG.default_input_limit

    def test_max_headline_length_is_reasonable(self):
        assert 40 <= FEED_CURATOR_CONFIG.max_headline_length <= 200

    def test_max_headline_length_is_80(self):
        assert FEED_CURATOR_CONFIG.max_headline_length == 80


class TestValidCategories:
    """Verify valid_categories contains the expected values."""

    def test_has_ai_category(self):
        assert "AI" in FEED_CURATOR_CONFIG.valid_categories

    def test_has_fintech_category(self):
        assert "Fintech" in FEED_CURATOR_CONFIG.valid_categories

    def test_has_ai_in_banking_category(self):
        assert "AI in Banking" in FEED_CURATOR_CONFIG.valid_categories

    def test_has_funding_category(self):
        assert "Funding" in FEED_CURATOR_CONFIG.valid_categories

    def test_has_healthtech_category(self):
        assert "HealthTech" in FEED_CURATOR_CONFIG.valid_categories

    def test_has_devtools_category(self):
        assert "DevTools" in FEED_CURATOR_CONFIG.valid_categories

    def test_no_duplicate_categories(self):
        cats = FEED_CURATOR_CONFIG.valid_categories
        assert len(cats) == len(set(cats))

    def test_all_categories_are_strings(self):
        for cat in FEED_CURATOR_CONFIG.valid_categories:
            assert isinstance(cat, str)
            assert len(cat) > 0


class TestSkipKeywords:
    """Verify spam keywords are present and correctly formed."""

    def test_skip_keywords_not_empty(self):
        assert len(FEED_CURATOR_CONFIG.skip_keywords) > 0

    def test_gambling_keywords_present(self):
        keywords = FEED_CURATOR_CONFIG.skip_keywords
        # At least one gambling-related keyword must be present
        gambling_related = {"bet365", "cassino", "casino", "apostas esportivas", "sports bet"}
        assert gambling_related & set(keywords), "No gambling keywords found"

    def test_all_keywords_lowercase(self):
        for kw in FEED_CURATOR_CONFIG.skip_keywords:
            assert kw == kw.lower(), f"Keyword '{kw}' is not lowercase"

    def test_no_empty_keywords(self):
        for kw in FEED_CURATOR_CONFIG.skip_keywords:
            assert len(kw.strip()) > 0, "Found empty keyword in skip_keywords"

    def test_no_duplicate_keywords(self):
        kws = FEED_CURATOR_CONFIG.skip_keywords
        assert len(kws) == len(set(kws))


class TestSystemPrompt:
    """Verify the LLM system prompt is well-formed."""

    def test_contains_persona_name(self):
        assert FEED_CURATOR_CONFIG.persona_name in CURATOR_SYSTEM_PROMPT

    def test_mentions_latin_america(self):
        prompt_lower = CURATOR_SYSTEM_PROMPT.lower()
        assert "latin america" in prompt_lower or "latam" in prompt_lower

    def test_specifies_language(self):
        assert "Portuguese" in CURATOR_SYSTEM_PROMPT or "pt-BR" in CURATOR_SYSTEM_PROMPT

    def test_no_em_dash_instruction(self):
        # The prompt should instruct not to use em dash per copywriting rules
        assert "em dash" in CURATOR_SYSTEM_PROMPT.lower()

    def test_prompt_is_non_empty_string(self):
        assert isinstance(CURATOR_SYSTEM_PROMPT, str)
        assert len(CURATOR_SYSTEM_PROMPT) > 50


class TestUserPromptTemplate:
    """Verify the user prompt template formats correctly."""

    def test_template_has_limit_placeholder(self):
        assert "{limit}" in CURATOR_USER_PROMPT_TEMPLATE

    def test_template_has_signals_json_placeholder(self):
        assert "{signals_json}" in CURATOR_USER_PROMPT_TEMPLATE

    def test_template_formats_with_values(self):
        result = CURATOR_USER_PROMPT_TEMPLATE.format(
            limit=10,
            signals_json='[{"content_hash": "abc123"}]',
        )
        assert "10" in result
        assert "abc123" in result

    def test_template_mentions_content_hash(self):
        # LLM must know to return content_hash for matching
        assert "content_hash" in CURATOR_USER_PROMPT_TEMPLATE

    def test_template_mentions_json_array(self):
        template_lower = CURATOR_USER_PROMPT_TEMPLATE.lower()
        assert "json array" in template_lower or "json" in template_lower


class TestFeedCuratorConfigImmutability:
    """Verify the config dataclass is frozen (immutable)."""

    def test_config_is_frozen(self):
        import dataclasses
        assert FEED_CURATOR_CONFIG.__dataclass_params__.frozen is True

    def test_cannot_mutate_config(self):
        import pytest
        with pytest.raises((TypeError, AttributeError)):
            FEED_CURATOR_CONFIG.version = "9.9.9"  # type: ignore[misc]
