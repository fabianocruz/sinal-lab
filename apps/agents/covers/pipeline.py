"""Cover image generation pipeline orchestrator.

Ties together all 4 stages: prompt generation, image generation,
brand overlay, and upload. Handles partial failures gracefully.

Usage:
    from apps.agents.covers.pipeline import CoverPipeline
    from apps.agents.covers.prompt_generator import CoverBriefing

    pipeline = CoverPipeline()
    result = pipeline.run(CoverBriefing(
        headline="Nubank testa agentes de AI",
        lede="O maior banco digital da LATAM...",
        agent="radar",
        edition=30,
    ))
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from apps.agents.covers.config import AGENT_COLORS, DEFAULT_AGENT_COLOR
from apps.agents.covers.overlay import BrandOverlay, OverlayConfig
from apps.agents.covers.prompt_generator import CoverBriefing, CoverPromptGenerator
from apps.agents.covers.recraft import RecraftClient
from apps.agents.covers.uploader import BlobUploader

logger = logging.getLogger(__name__)


@dataclass
class CoverResult:
    """Result of cover image generation."""

    images: List[Dict[str, object]] = field(default_factory=list)
    prompt_used: str = ""
    agent: str = ""
    errors: List[str] = field(default_factory=list)


class CoverPipeline:
    """End-to-end cover image generation pipeline.

    Stages: prompt generation → image generation → brand overlay → upload.
    Each stage degrades gracefully. If any stage fails completely,
    the pipeline returns partial results or an error.
    """

    def __init__(
        self,
        prompt_generator: Optional[CoverPromptGenerator] = None,
        image_generator: Optional[RecraftClient] = None,
        uploader: Optional[BlobUploader] = None,
    ) -> None:
        self._prompt_gen = prompt_generator or CoverPromptGenerator()
        self._image_gen = image_generator or RecraftClient()
        self._uploader = uploader or BlobUploader()

    def run(self, briefing: CoverBriefing, variations: int = 3) -> CoverResult:
        """Execute the full cover generation pipeline.

        Args:
            briefing: Editorial briefing (headline, lede, agent, edition, dq_score).
            variations: Number of image variations to generate (1-3).

        Returns:
            CoverResult with list of uploaded image URLs and any errors.
        """
        result = CoverResult(agent=briefing.agent)

        # Stage 1: Generate image prompt
        prompt = self._prompt_gen.generate_prompt(briefing)
        if not prompt:
            result.errors.append("Prompt generation failed")
            return result
        result.prompt_used = prompt

        # Stage 2: Generate images
        images = self._image_gen.generate(prompt, variations=variations)
        if not images:
            result.errors.append("All image generations failed")
            return result

        if len(images) < variations:
            result.errors.append(
                f"Partial image generation: {len(images)}/{variations} succeeded"
            )

        # Stage 3 + 4: Overlay and upload each image
        agent_color = AGENT_COLORS.get(briefing.agent, DEFAULT_AGENT_COLOR)
        overlay = BrandOverlay(OverlayConfig(
            agent=briefing.agent,
            agent_color=agent_color,
            dq_score=briefing.dq_score,
            edition=briefing.edition,
        ))

        for img in images:
            # Apply overlay
            try:
                composited = overlay.apply(img.image_bytes)
            except Exception as e:
                result.errors.append(f"Overlay failed for variation {img.variation}: {e}")
                continue

            # Upload to Vercel Blob
            filename = f"covers/{briefing.agent}/ed{briefing.edition}-v{img.variation}.png"
            uploaded = self._uploader.upload(composited, filename)
            if not uploaded:
                result.errors.append(f"Upload failed for variation {img.variation}")
                continue

            result.images.append({
                "url": uploaded.url,
                "variation": img.variation,
                "pathname": uploaded.pathname,
            })

        return result
