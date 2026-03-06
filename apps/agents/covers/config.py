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

# Per-agent visual identity — distinct objects and composition for each agent.
# Injected into the art director prompt to prevent visual convergence.
AGENT_VISUAL_IDENTITY: Dict[str, str] = {
    "radar": (
        "RADAR tracks tech trends and emerging tools. "
        "Visual vocabulary: radar screens, data dashboards with line charts, "
        "network node graphs, signal waves, antenna arrays, sonar pulses. "
        "Composition style: top-down data visualization, floating UI panels."
    ),
    "funding": (
        "FUNDING tracks venture capital and investment rounds in LATAM. "
        "Visual vocabulary: stacked coins, rising bar charts, handshake silhouettes, "
        "vault doors, golden ratio spirals, ticker tape, portfolio grids. "
        "Composition style: bold central symbol (coins, chart), strong diagonal energy."
    ),
    "codigo": (
        "CODIGO covers developer tools, infrastructure, and code. "
        "Visual vocabulary: code editor windows, terminal prompts, Git branch diagrams, "
        "circuit board traces, mechanical gears, package boxes, API endpoint diagrams. "
        "Composition style: layered floating panels, code-like grid structure."
    ),
    "mercado": (
        "MERCADO maps the LATAM startup ecosystem — companies, cities, sectors. "
        "Visual vocabulary: geographic maps with glowing pins, company logo grids, "
        "ecosystem tree diagrams, city skyline silhouettes, connection webs, heat maps. "
        "Composition style: bird's-eye view map or grid layout, scattered data points."
    ),
    "sintese": (
        "SINTESE is the weekly editorial newsletter — synthesizes all signals. "
        "Visual vocabulary: newspaper front pages, editorial desk with multiple screens, "
        "signal waveforms merging into one, mosaic of news tiles, megaphone, "
        "briefing folder, collage of data sources. "
        "Composition style: layered collage, multiple overlapping elements."
    ),
}

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
    "You receive: a headline + lede from an editorial briefing, "
    "plus the agent's visual identity guide.\n"
    "You produce: an image prompt for Recraft V3.\n\n"
    "CRITICAL — EACH COVER MUST BE UNIQUE:\n"
    "1. The image must visually represent the SPECIFIC STORY topic.\n"
    "2. Use the agent's visual vocabulary (provided below) to select objects.\n"
    "3. NEVER default to 'city skyline' or 'buildings' unless the story is about cities.\n"
    "4. Two covers for the same agent in different weeks must look completely different.\n\n"
    "VISUAL RULES:\n"
    "1. Show CONCRETE objects from the agent's visual vocabulary that match the story.\n"
    "2. Dark background — but the SUBJECT must be brightly lit and clearly visible. "
    "Think cinematic lighting: dramatic rim lights, strong directional light, "
    "glowing accents. The subject should POP against the dark background.\n"
    "3. {agent_color} is the accent color — use it for lighting, glows, and highlights.\n"
    "4. Style: photorealistic, cinematic, tech magazine editorial quality. "
    "Sharp focus, high detail, dramatic lighting.\n"
    "5. Composition: main subject right-of-center, "
    "30% left side slightly less busy for text overlay.\n"
    "6. NEVER include text, words, letters, or numbers in the image.\n"
    "7. The image must be clearly recognizable as a 400x200px thumbnail.\n\n"
    "AGENT VISUAL IDENTITY:\n{agent_visual_identity}\n\n"
    "OUTPUT: Only the image prompt in English, maximum 120 words.\n"
    "Format: 1820x1024 horizontal composition."
)
