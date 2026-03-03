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
# Image dimensions
# ---------------------------------------------------------------------------

# Final OG image size (standard Open Graph / social media)
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 628

# Recraft V3 generation size — must be from their fixed list of valid sizes.
# 1820x1024 is the closest 16:9 option; we resize to IMAGE_WIDTH x IMAGE_HEIGHT
# after generation in the overlay step.
RECRAFT_WIDTH = 1820
RECRAFT_HEIGHT = 1024

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
    "CRITICAL — CONTEXTUAL IMAGERY:\n"
    "Each cover MUST be visually specific to the story. A reader should look "
    "at the image and immediately understand what sector or topic it covers.\n"
    "- Banking story → vaults, cards, digital banking interfaces\n"
    "- Autonomous vehicles → cars, roads, sensors, lidar\n"
    "- AI/ML story → neural networks, data pipelines, chips\n"
    "- Fintech funding → growth charts, coins, investment symbols\n"
    "- Healthcare → medical devices, molecules, lab environments\n"
    "- Logistics → warehouses, drones, supply chain\n"
    "NEVER produce a generic 'futuristic tech' image that could fit any story.\n\n"
    "VISUAL RULES:\n"
    "1. Show CONCRETE objects related to the story's industry/sector.\n"
    "2. Use the company's actual product domain as visual reference.\n"
    "3. Background ALWAYS dark (#0A0A0B to #1A1A1F).\n"
    "4. Dominant accent color: {agent_color} — use it for lighting, glows, highlights.\n"
    "5. Style: tech magazine editorial, cinematic, photorealistic.\n"
    "6. Composition: leave 40% left side clean for text overlay.\n"
    "7. Mood: serious, data-driven, futuristic but grounded in reality.\n"
    "8. NEVER include text, words, or letters in the image.\n"
    "9. NEVER use cartoon, clipart, or generic stock photo style.\n"
    "10. Include Latin American elements when relevant "
    "(skylines, architecture, cultural references).\n\n"
    "OUTPUT: Only the image prompt in English, maximum 120 words.\n"
    "Format: 1820x1024 horizontal composition."
)
