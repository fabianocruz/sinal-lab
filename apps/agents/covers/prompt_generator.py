"""LLM-powered image prompt generator for cover images.

Uses the shared LLMClient to transform editorial briefings (headline + lede)
into Recraft V3 image prompts following the Sinal art direction guidelines.

Architecture:
    pipeline.py (orchestrator)
    └── prompt_generator.py  <- this module
        └── LLMClient.generate()  <- shared LLM layer
"""

import logging
from dataclasses import dataclass
from typing import Optional

from apps.agents.base.llm import LLMClient
from apps.agents.covers.config import (
    AGENT_COLORS,
    ART_DIRECTOR_SYSTEM_PROMPT,
    DEFAULT_AGENT_COLOR,
)

logger = logging.getLogger(__name__)

MAX_PROMPT_WORDS = 150
MAX_PROMPT_CHARS = 1000  # Recraft V3 API limit


@dataclass
class CoverBriefing:
    """Input briefing for cover image generation."""

    headline: str
    lede: str
    agent: str
    edition: int
    dq_score: Optional[float] = None


class CoverPromptGenerator:
    """Generates Recraft V3 image prompts from editorial briefings.

    Uses LLMClient to produce concise image prompts following the
    Sinal art direction guidelines. Falls back gracefully (returns None)
    when the client is unavailable or generation fails.
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        """Initialize with an optional LLMClient (creates one if not provided)."""
        self._client = client if client is not None else LLMClient()

    @property
    def is_available(self) -> bool:
        """Check if the underlying LLM client can generate prompts."""
        return self._client.is_available

    def generate_prompt(self, briefing: CoverBriefing) -> Optional[str]:
        """Generate a Recraft V3 image prompt from an editorial briefing.

        Args:
            briefing: Editorial briefing with headline, lede, agent, etc.

        Returns:
            Image prompt string (max 150 words), or None if generation fails.
        """
        if not briefing.headline.strip():
            logger.warning("Empty headline in cover briefing")
            return None

        if not self.is_available:
            logger.warning("LLM client unavailable for cover prompt generation")
            return None

        agent_color = AGENT_COLORS.get(briefing.agent, DEFAULT_AGENT_COLOR)
        system_prompt = ART_DIRECTOR_SYSTEM_PROMPT.replace("{agent_color}", agent_color)

        user_prompt = (
            f"Generate an image prompt for this editorial cover:\n\n"
            f"Agent: {briefing.agent.upper()}\n"
            f"Accent color: {agent_color}\n"
            f"Headline: {briefing.headline}\n"
            f"Lede: {briefing.lede}\n\n"
            f"Remember: dark background, {briefing.agent.upper()} agent color "
            f"({agent_color}) as dominant accent. Editorial magazine cover aesthetic. "
            f"Leave left 40% open for text overlay. No text in image."
        )

        result = self._client.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=0.8,
        )

        if not result or not result.strip():
            logger.warning("LLM returned empty prompt for cover generation")
            return None

        truncated = _truncate_to_max_words(result.strip())
        return _truncate_to_max_chars(truncated)


def _truncate_to_max_words(text: str, max_words: int = MAX_PROMPT_WORDS) -> str:
    """Truncate text to max_words, preserving whole words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _truncate_to_max_chars(text: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """Truncate text to max_chars, cutting at the last complete sentence or word."""
    if len(text) <= max_chars:
        return text
    # Cut at last space before the limit to avoid breaking mid-word
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space]
    return truncated
