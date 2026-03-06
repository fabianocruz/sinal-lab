"""Tests for cover image generation configuration."""

from apps.agents.covers.config import (
    AGENT_COLORS,
    AGENT_VISUAL_IDENTITY,
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


def test_visual_identity_has_all_five_agents():
    expected = {"radar", "funding", "codigo", "mercado", "sintese"}
    assert set(AGENT_VISUAL_IDENTITY.keys()) == expected


def test_visual_identity_keys_match_agent_colors():
    assert set(AGENT_VISUAL_IDENTITY.keys()) == set(AGENT_COLORS.keys())


def test_visual_identity_entries_are_non_empty_strings():
    for agent, identity in AGENT_VISUAL_IDENTITY.items():
        assert isinstance(identity, str), f"{agent} identity is not a string"
        assert len(identity) > 50, f"{agent} identity is too short"


def test_visual_identity_entries_contain_visual_vocabulary():
    for agent, identity in AGENT_VISUAL_IDENTITY.items():
        assert "Visual vocabulary:" in identity, f"{agent} missing visual vocabulary"
        assert "Composition style:" in identity, f"{agent} missing composition style"


def test_visual_identity_agents_are_distinct():
    """Each agent's visual vocabulary should be unique — no copy-paste."""
    identities = list(AGENT_VISUAL_IDENTITY.values())
    assert len(set(identities)) == len(identities)


def test_system_prompt_contains_key_directives():
    assert "dark" in ART_DIRECTOR_SYSTEM_PROMPT.lower()
    assert "{agent_color}" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "120 words" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "NEVER" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "Latin America" in ART_DIRECTOR_SYSTEM_PROMPT


def test_system_prompt_has_visual_identity_placeholder():
    assert "{agent_visual_identity}" in ART_DIRECTOR_SYSTEM_PROMPT


def test_system_prompt_emphasizes_cinematic_lighting():
    prompt_lower = ART_DIRECTOR_SYSTEM_PROMPT.lower()
    assert "cinematic" in prompt_lower
    assert "brightly lit" in prompt_lower
    assert "rim light" in prompt_lower


def test_system_prompt_requires_unique_covers():
    assert "EACH COVER MUST BE UNIQUE" in ART_DIRECTOR_SYSTEM_PROMPT


def test_default_agent_color_is_white():
    assert DEFAULT_AGENT_COLOR == "#FFFFFF"


def test_recraft_dimensions_are_valid_api_size():
    """Recraft V3 only accepts specific dimension pairs."""
    assert RECRAFT_WIDTH == 1820
    assert RECRAFT_HEIGHT == 1024
