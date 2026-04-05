"""Configuration for the Feed Curator agent."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class FeedCuratorConfig:
    """Feed Curator configuration.

    Attributes:
        version: Agent version string.
        persona_name: Editorial persona used in LLM prompts.
        schedule_hours: How often the curator runs (in hours).
        default_input_limit: Max signals to load from DB per run.
        default_output_limit: Max curated items to produce per run.
        valid_categories: Allowed category values for curation output.
        skip_keywords: Keywords that trigger spam filtering (pre-LLM).
        max_headline_length: Max characters for editorial headlines.
    """

    version: str = "0.1.0"
    persona_name: str = "Ana Torres"
    schedule_hours: int = 4
    default_input_limit: int = 100
    default_output_limit: int = 20
    valid_categories: List[str] = field(default_factory=lambda: [
        "AI",
        "Fintech",
        "Banking",
        "Startup",
    ])
    skip_keywords: List[str] = field(default_factory=lambda: [
        "apostas esportivas",
        "sports bet",
        "bet365",
        "cassino",
        "casino",
        "horoscopo",
        "previsao politica",
    ])
    max_headline_length: int = 80


FEED_CURATOR_CONFIG = FeedCuratorConfig()


# LLM system prompt for the Ana Torres persona
CURATOR_SYSTEM_PROMPT = (
    f"You are {FEED_CURATOR_CONFIG.persona_name}, editorial curator for Sinal.tech. "
    "You select and contextualize the most relevant signals for founders, CTOs and VCs "
    "building technology in Latin America. You write in Portuguese (Brazil). "
    "Do NOT use em dash."
)

CURATOR_USER_PROMPT_TEMPLATE = (
    "You are Ana Torres, editorial curator for Sinal.tech. "
    "From these signals, select the {limit} most relevant for founders, CTOs and VCs "
    "building technology in Latin America. "
    "For EACH selected signal, return JSON: "
    '{{"editorial_headline": string (pt-BR, max 80 chars), '
    '"editorial_context": string (pt-BR, 1-2 sentences why this matters), '
    '"relevance_score": int 0-100, '
    '"category": "AI"|"Fintech"|"Banking"|"Startup"}}. '
    "SKIP: sports bets, political predictions, generic news, spam. "
    "PRIORITIZE: funding rounds, product launches, technical insights, "
    "regulatory changes, LATAM-specific news.\n\n"
    "Return a JSON array. Each object must also include the original "
    '"content_hash" field so I can match it back to the source signal.\n\n'
    "Signals:\n{signals_json}"
)
