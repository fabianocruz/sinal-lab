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
    "You receive: a headline + lede from a publication.\n"
    "You produce: an image prompt for Recraft V3 (realistic_image).\n\n"
    "RULES:\n"
    "1. Background ALWAYS dark (#0A0A0B to #1A1A1F).\n"
    "2. Dominant accent color: {agent_color} — use it for lighting, glows, highlights.\n"
    "3. Style: photorealistic, tech magazine editorial, cinematic.\n"
    "4. Composition: leave space for overlay (badges at top, gradient at bottom).\n"
    "5. Mood: serious, data-driven, futuristic but grounded in reality.\n"
    "6. NEVER include text, words, or letters in the image.\n"
    "7. NEVER use cartoon, clipart, or generic stock photo style.\n"
    "8. Include Latin American elements when relevant "
    "(skylines, architecture, cultural references).\n\n"
    "CRITICAL — CONTEXTUAL IMAGERY:\n"
    "Each cover MUST show CONCRETE OBJECTS related to the story's industry/sector. "
    "A reader should look at the image and immediately understand what topic it covers. "
    "NEVER produce a generic 'futuristic tech' image that could fit any story.\n\n"
    "Sector examples:\n"
    "- Banking/Fintech → vaults, credit cards, payment terminals, candlestick charts\n"
    "- Healthcare → medical devices, hospital equipment, diagnostic interfaces\n"
    "- Logistics → automated warehouses, delivery drones, containers, truck fleets\n"
    "- AI/ML → data centers, GPUs, server racks, metric dashboards, terminal interfaces\n"
    "- E-commerce → shopping carts, warehouses, checkout screens\n"
    "- Regulation → gavels, official documents, government buildings\n"
    "- DevTools → code terminals, IDEs, network racks, switches\n"
    "- Autonomous vehicles → cars, roads, sensors, lidar\n\n"
    "GOLDEN RULE: if the story is about 'Nubank tests AI agents', the image shows "
    "a futuristic banking environment with AI elements — NOT an 'abstract constellation "
    "of connected dots'.\n\n"
    "OUTPUT: Only the image prompt in English, maximum 150 words.\n"
    "Format: 1820x1024 horizontal composition."
)

# ---------------------------------------------------------------------------
# Article cover art direction — visual vocabulary by article type
# ---------------------------------------------------------------------------

ARTICLE_COLOR = "#59FFB4"  # Verde (Santos de Machine)
ARTICLE_BADGE_TEXT = "ARTIGO"

ARTICLE_ART_DIRECTION: Dict[str, str] = {
    "diary": (
        "ARTICLE TYPE: Construction diary (weekly series).\n"
        "CRITICAL: The image MUST depict the SPECIFIC TOPIC described in the title "
        "and thesis, NOT a generic developer workstation. Each diary entry covers a "
        "different subject. Choose the visual that best represents THAT subject:\n"
        "- If about deploy/CI/CD: rocket launch pad, conveyor belt delivering packages\n"
        "- If about data pipelines: water treatment plant, industrial pipes, flowing data streams\n"
        "- If about AI agents: robotic arms, autonomous machines, factory floor with robots\n"
        "- If about email/communication: post office sorting room, mail tubes, signal towers\n"
        "- If about security/LGPD: vault doors, shield walls, fortified architecture\n"
        "- If about APIs: bridges connecting buildings, highway interchanges, train stations\n"
        "- If about frontend: glass facades, window displays, architectural blueprints\n"
        "- If about pricing/marketplace: bazaar stalls, trading floor, market square\n"
        "Use METAPHORICAL OBJECTS from the physical world, not literal screens/monitors. "
        "Cinematic, dramatic lighting. Dominant color: green (#59FFB4).\n"
    ),
    "essay": (
        "ARTICLE TYPE: Opinion essay (standalone).\n"
        "Visual vocabulary: conceptual, metaphorical, provocative. One strong unexpected "
        "visual idea that captures the thesis. More artistic than briefing covers. "
        "Focus on the argument, not the sector. Think editorial photography meets "
        "conceptual art. Use METAPHORICAL imagery, not literal tech objects.\n"
    ),
    "tutorial": (
        "ARTICLE TYPE: Tutorial / How-to.\n"
        "Visual vocabulary: show the RESULT of the tutorial, not a person coding. "
        "The tool working, the system running, the output visible. Tangible, everyday "
        "with a tech twist. Prefer physical-world metaphors over screens and monitors.\n"
    ),
}
