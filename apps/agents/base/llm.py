"""Shared LLM client for Sinal.lab agents.

Wraps the Anthropic Python SDK to provide a simple generate() interface
with graceful degradation. If ANTHROPIC_API_KEY is not set or the SDK
is not installed, all calls return None without raising.

Architecture:
    This module is the shared LLM layer used by all agent writers:

        base/llm.py (this module)
        └── LLMClient.generate()   → Anthropic messages API
            ├── sintese/writer.py   (newsletter editorial content)
            └── (future agents)     (reusable by RADAR, CODIGO, etc.)

Usage:
    from apps.agents.base.llm import LLMClient
    client = LLMClient()
    if client.is_available:
        result = client.generate("Summarize this article", system_prompt="...")
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for the LLM client."""

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 1024
    temperature: float = 0.7
    api_key_env: str = "ANTHROPIC_API_KEY"


class LLMClient:
    """Anthropic Claude API client with graceful degradation.

    Returns None on any failure (missing key, SDK not installed,
    API errors, rate limits). Callers should always check the return
    value and fall back to template-based output.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self._config = config or LLMConfig()
        self._api_key = os.environ.get(self._config.api_key_env, "")

    @property
    def is_available(self) -> bool:
        """Check if the LLM client can make API calls."""
        return _ANTHROPIC_AVAILABLE and bool(self._api_key)

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Generate text using Claude API.

        Args:
            user_prompt: The user message to send.
            system_prompt: Optional system prompt for editorial voice.
            max_tokens: Override config max_tokens for this call.
            temperature: Override config temperature for this call.

        Returns:
            Generated text string, or None on any failure.
        """
        if not self.is_available:
            return None

        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._config.model,
                max_tokens=max_tokens or self._config.max_tokens,
                temperature=temperature if temperature is not None else self._config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            if not response.content:
                logger.warning("LLM returned empty response")
                return None

            return response.content[0].text

        except anthropic.APIError as e:
            logger.warning("LLM API error: %s", e)
            return None
        except Exception as e:
            logger.warning("LLM unexpected error: %s", e)
            return None
