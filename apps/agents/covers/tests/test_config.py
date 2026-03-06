"""Tests for cover image generation configuration."""

from apps.agents.covers.config import (
    AGENT_COLORS,
    ARTICLE_ART_DIRECTION,
    ARTICLE_BADGE_TEXT,
    ARTICLE_COLOR,
    ART_DIRECTOR_SYSTEM_PROMPT,
    DEFAULT_AGENT_COLOR,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MINI_BAR_COLORS,
    RECRAFT_HEIGHT,
    RECRAFT_WIDTH,
)


def test_agent_colors_has_all_five_agents():
    expected = {"radar", "funding", "codigo", "mercado", "sintese"}
    assert set(AGENT_COLORS.keys()) == expected


def test_agent_colors_are_valid_hex():
    for color in AGENT_COLORS.values():
        assert color.startswith("#")
        assert len(color) == 7


def test_mini_bar_colors_has_five_entries():
    assert len(MINI_BAR_COLORS) == 5


def test_image_dimensions_are_og_standard():
    assert IMAGE_WIDTH == 1200
    assert IMAGE_HEIGHT == 628


def test_system_prompt_contains_key_directives():
    assert "dark" in ART_DIRECTOR_SYSTEM_PROMPT.lower()
    assert "{agent_color}" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "150 words" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "NEVER" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "Latin America" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "GOLDEN RULE" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "realistic_image" in ART_DIRECTOR_SYSTEM_PROMPT


def test_system_prompt_has_sector_examples():
    for sector in ["Banking/Fintech", "Healthcare", "Logistics", "AI/ML",
                    "E-commerce", "Regulation", "DevTools"]:
        assert sector in ART_DIRECTOR_SYSTEM_PROMPT


def test_default_agent_color_is_white():
    assert DEFAULT_AGENT_COLOR == "#FFFFFF"


def test_recraft_dimensions_are_valid_api_size():
    """Recraft V3 only accepts specific dimension pairs."""
    assert RECRAFT_WIDTH == 1820
    assert RECRAFT_HEIGHT == 1024


# ---------------------------------------------------------------------------
# Article config tests
# ---------------------------------------------------------------------------

def test_article_color_is_valid_hex():
    assert ARTICLE_COLOR.startswith("#")
    assert len(ARTICLE_COLOR) == 7


def test_article_badge_text():
    assert ARTICLE_BADGE_TEXT == "ARTIGO"


def test_article_art_direction_has_three_types():
    assert set(ARTICLE_ART_DIRECTION.keys()) == {"diary", "essay", "tutorial"}


def test_article_art_direction_diary_mentions_deploy():
    diary = ARTICLE_ART_DIRECTION["diary"]
    assert "deploy" in diary.lower()


def test_article_art_direction_diary_uses_metaphors():
    """Diary art direction should encourage physical-world metaphors, not literal screens."""
    diary = ARTICLE_ART_DIRECTION["diary"]
    assert "metaphor" in diary.lower()
    assert "not literal" in diary.lower() or "not screens" in diary.lower() or "not literal screens" in diary.lower()


def test_article_art_direction_essay_is_conceptual():
    essay = ARTICLE_ART_DIRECTION["essay"]
    assert "conceptual" in essay.lower() or "metaphor" in essay.lower()


def test_article_art_direction_tutorial_is_tangible():
    tutorial = ARTICLE_ART_DIRECTION["tutorial"]
    assert "result" in tutorial.lower() or "tangible" in tutorial.lower()
