"""Configuration for the cover image generation pipeline.

Defines agent colors, overlay layout constants, Recraft API defaults,
and the art director system prompt used for image prompt generation.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Agent accent colors — single source of truth for covers.
# If the frontend constants.ts changes, update here too.
# ---------------------------------------------------------------------------

AGENT_COLORS: Dict[str, str] = {
    "radar": "#59FFB4",
    "funding": "#FF8A59",
    "codigo": "#59B4FF",
    "mercado": "#C459FF",
    "sintese": "#E8FF59",
}

DEFAULT_AGENT_COLOR = "#FFFFFF"

# Fixed order for the mini color bar (bottom-right of overlay)
MINI_BAR_COLORS: List[str] = [
    "#59FFB4",  # RADAR
    "#FF8A59",  # FUNDING
    "#59B4FF",  # CÓDIGO
    "#C459FF",  # MERCADO
    "#E8FF59",  # SÍNTESE
]

# ---------------------------------------------------------------------------
# Image generation defaults
# ---------------------------------------------------------------------------

IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 628

# ---------------------------------------------------------------------------
# Recraft V3 API defaults
# ---------------------------------------------------------------------------

RECRAFT_API_URL = "https://external.api.recraft.ai/v1/images/generations"
RECRAFT_DEFAULT_STYLE = "realistic_image"
RECRAFT_DEFAULT_MODEL = "recraftv3"
RECRAFT_TIMEOUT = 60.0  # seconds — image generation is slow

# ---------------------------------------------------------------------------
# Overlay layout constants
# ---------------------------------------------------------------------------

TOP_BAR_HEIGHT = 3
BADGE_MARGIN = 20
BADGE_PADDING_X = 12
BADGE_PADDING_Y = 6
GRADIENT_HEIGHT = 180
MINI_BAR_SEGMENT_WIDTH = 16
MINI_BAR_HEIGHT = 3
MINI_BAR_MARGIN = 20

# ---------------------------------------------------------------------------
# Art director system prompt for image prompt generation
# ---------------------------------------------------------------------------

ART_DIRECTOR_SYSTEM_PROMPT = (
    "You are the art director for Sinal, a tech intelligence platform "
    "for Latin America.\n\n"
    "You receive: a headline + lede from an editorial briefing.\n"
    "You produce: an image prompt for Recraft V3.\n\n"
    "RULES:\n"
    "1. The image must ILLUSTRATE the story, not describe it literally.\n"
    "2. Use strong visual metaphors (e.g., funding = rocket, growth = rising graph).\n"
    "3. Background ALWAYS dark (#0A0A0B to #1A1A1F).\n"
    "4. Dominant accent color: {agent_color}\n"
    "5. Style: tech magazine editorial, cinematic.\n"
    "6. Composition: leave 40% left side clean for title overlay.\n"
    "7. Mood: serious, data-driven, futuristic but plausible.\n"
    "8. NEVER include text in the image (text comes in the overlay).\n"
    "9. NEVER use cartoon, clipart, or generic stock photo style.\n"
    "10. Include elements that reference Latin America when possible "
    "(skylines, stylized maps, subtle cultural references).\n\n"
    "OUTPUT: Only the image prompt in English, maximum 150 words.\n"
    "Format: 1200x628 horizontal composition."
)
