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

# Descriptive color names for image prompts — avoids AI models rendering
# hex codes as literal text in the generated image.
AGENT_COLOR_NAMES: Dict[str, str] = {
    "radar": "neon mint green",
    "funding": "warm coral orange",
    "codigo": "electric sky blue",
    "mercado": "vivid purple",
    "sintese": "bright lime yellow",
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

TOP_BAR_HEIGHT = 4
BADGE_MARGIN = 24
BADGE_PADDING_X = 16
BADGE_PADDING_Y = 8
GRADIENT_HEIGHT = 220
MINI_BAR_SEGMENT_WIDTH = 20
MINI_BAR_HEIGHT = 4
MINI_BAR_MARGIN = 24

# ---------------------------------------------------------------------------
# Art director system prompt for image prompt generation
# ---------------------------------------------------------------------------

ART_DIRECTOR_SYSTEM_PROMPT = (
    "You are the art director for Sinal, a tech intelligence platform "
    "for Latin America.\n\n"
    "You receive: a headline + lede from a publication.\n"
    "You produce: an image prompt for Recraft V3 (realistic_image).\n\n"
    "RULES:\n"
    "1. Background MUST be dark/night (#0A0A0B to #1A1A1F). NO daylight, NO sunsets, "
    "NO bright skies. The scene is ALWAYS at night or in a dark interior.\n"
    "2. Dominant accent color: {agent_color_name} — use it for neon glows, rim lighting, "
    "reflections, LED indicators, holographic elements. The accent should POP against the dark.\n"
    "3. Style: photorealistic, cinematic, shallow depth of field (f/1.4-2.8). "
    "Think Blade Runner 2049 meets Bloomberg Businessweek cover photography.\n"
    "4. Composition: subject fills 60-80% of frame. Use CLOSE-UP or MEDIUM shots, "
    "NOT wide establishing shots. Leave top 10% and bottom 20% slightly darker for overlays.\n"
    "5. Lighting: dramatic, volumetric. Strong key light from one side. "
    "Use {agent_color_name} as rim light or environmental neon. "
    "Visible light rays, lens flare, or bokeh encouraged.\n"
    "6. NEVER include text, words, letters, numbers, or UI elements in the image.\n"
    "7. NEVER use cartoon, clipart, stock photo, or corporate office aesthetics.\n"
    "8. When relevant, include Latin American visual cues (Sao Paulo skyline at night, "
    "tropical vegetation with neon, brutalist LATAM architecture).\n\n"
    "CRITICAL — SPECIFICITY OVER GENERALITY:\n"
    "Each cover MUST show ONE hero object or scene that is SPECIFIC to the story. "
    "Pick the single most striking visual element from the headline. "
    "Photograph it like a magazine cover: up close, dramatic, beautiful.\n\n"
    "GOOD examples:\n"
    "- 'AI chip startup raises $400M' → extreme close-up of a glowing AI chip on a dark "
    "circuit board, {agent_color_name} traces on the silicon, shallow DOF\n"
    "- 'Data centers in space' → orbital station with server modules floating against "
    "Earth's dark side, {agent_color_name} status lights blinking\n"
    "- 'Fintech raises Series A' → close-up of a sleek payment terminal with "
    "{agent_color_name} LED indicators, dark marble counter, city lights reflected\n"
    "- 'LATAM startup ecosystem' → aerial night view of Sao Paulo's Faria Lima district "
    "with {agent_color_name} data visualization overlaid on the skyline\n\n"
    "BAD examples (NEVER do this):\n"
    "- Generic open-plan office with monitors\n"
    "- Conference room with charts on table\n"
    "- Wide shot of server room corridor\n"
    "- Any scene that could be a stock photo\n"
    "- Pile of coins, stacks of cash, briefcases of money (finance cliche)\n"
    "- Handshakes, charts going up, arrows/rockets\n"
    "- Generic payment terminals/POS machines when headline is about credit infrastructure, "
    "FIDCs, securitization, or B2B finance (POS only fits retail/consumer payments)\n\n"
    "GEOGRAPHIC FIDELITY (CRITICAL):\n"
    "If the headline cites a specific country/city, the visual must match UNAMBIGUOUSLY. "
    "Never default to a different LATAM skyline because it is prettier.\n"
    "- Mexico → Mexico City's Angel de la Independencia column, Torre Reforma, or Torre "
    "Latinoamericana. NEVER use the Buenos Aires Obelisco for Mexico stories.\n"
    "- Argentina → Buenos Aires Obelisco or Puerto Madero bridges.\n"
    "- Brazil → Sao Paulo's Ponte Estaiada / Avenida Paulista, or Rio's Christ / Copacabana.\n"
    "- Chile → Santiago's Gran Torre Santiago or Andes backdrop.\n"
    "- Colombia → Bogota's Cerro de Monserrate or Medellin's Metrocable.\n"
    "- Peru → Lima's Huaca Pucllana or Miraflores coastline.\n"
    "- Puerto Rico → San Juan's El Morro or Condado coastline.\n\n"
    "HEADLINE → HERO OBJECT MAPPING (use as priors):\n"
    "- 'FIDC / securitization / credit fund' → close-up of paper ledger/contract with "
    "seal and signature, dramatic lighting, NOT payment terminals.\n"
    "- 'AI agents / LLM / agentic' → humanoid silhouette made of light, or interconnected "
    "nodes of light, neural network textures.\n"
    "- 'Valuation / mega-round' → magnified cap table page, OR a single banknote close-up "
    "(ONE bill, not piles), OR vault door ajar with {agent_color_name} light leaking out.\n"
    "- 'Embedded finance / commerce infra' → API diagram as glowing circuits etched on "
    "dark glass, NOT shopping carts.\n"
    "- 'Consumer credit' → a single credit card seen edge-on with {agent_color_name} "
    "chip glow, OR a minimalist loan agreement page.\n"
    "- When multiple themes compete in the headline, pick the MOST SPECIFIC one "
    "(FIDCs beats 'fintech generically').\n\n"
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
        "Cinematic, dramatic lighting. Dominant color: neon mint green.\n"
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
