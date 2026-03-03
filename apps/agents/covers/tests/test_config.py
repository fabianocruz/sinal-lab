"""Tests for cover image generation configuration."""

from apps.agents.covers.config import (
    AGENT_COLORS,
    ART_DIRECTOR_SYSTEM_PROMPT,
    DEFAULT_AGENT_COLOR,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MINI_BAR_COLORS,
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


def test_default_agent_color_is_white():
    assert DEFAULT_AGENT_COLOR == "#FFFFFF"
