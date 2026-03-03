"""Brand overlay compositor for cover images.

Applies Sinal visual identity elements on top of AI-generated images
using Pillow: agent color bar, badge, logo, gradient, and mini color bar.

Architecture:
    pipeline.py (orchestrator)
    └── overlay.py  <- this module
        └── Pillow (PIL)
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from apps.agents.covers.config import (
    BADGE_MARGIN,
    BADGE_PADDING_X,
    BADGE_PADDING_Y,
    GRADIENT_HEIGHT,
    MINI_BAR_COLORS,
    MINI_BAR_HEIGHT,
    MINI_BAR_MARGIN,
    MINI_BAR_SEGMENT_WIDTH,
    TOP_BAR_HEIGHT,
)

logger = logging.getLogger(__name__)


@dataclass
class OverlayConfig:
    """Configuration for the brand overlay compositor."""

    agent: str
    agent_color: str
    dq_score: Optional[float] = None
    edition: int = 1


class BrandOverlay:
    """Applies Sinal brand overlay to AI-generated cover images.

    Overlay elements:
    - Top: 3px color bar in agent accent color
    - Top-left: Agent badge with DQ score on dark background
    - Top-right: "Sinal" text logo on dark background
    - Bottom: 180px gradient fade (transparent to 70% black)
    - Bottom-left: "sinal.tech" URL text
    - Bottom-right: Mini 5-color bar (one per agent)
    """

    def __init__(self, config: OverlayConfig) -> None:
        """Initialize with overlay configuration (agent, color, scores)."""
        self._config = config

    def apply(self, image_bytes: bytes) -> bytes:
        """Apply brand overlay to a raw image.

        Args:
            image_bytes: Raw PNG/JPEG bytes of the source image.

        Returns:
            PNG bytes of the composited image.

        Raises:
            ValueError: If image_bytes cannot be decoded.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Cannot decode image: {e}") from e

        # Ensure RGBA mode — required for alpha_composite blending
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        width, height = img.size

        # Create a transparent overlay layer — all elements are drawn here,
        # then composited onto the source image in a single alpha blend pass
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        color_rgb = _hex_to_rgb(self._config.agent_color)

        # 1. Top color bar
        draw.rectangle([(0, 0), (width, TOP_BAR_HEIGHT)], fill=(*color_rgb, 255))

        # 2. Badge (top-left)
        self._draw_badge(draw, color_rgb)

        # 3. Logo (top-right)
        self._draw_logo(draw, width)

        # 4. Bottom gradient
        self._draw_gradient(draw, width, height)

        # 5. URL text (bottom-left)
        self._draw_url(draw, height)

        # 6. Mini color bar (bottom-right)
        self._draw_mini_bar(draw, width, height)

        # Alpha-composite: blend overlay layer onto the source image
        result = Image.alpha_composite(img, overlay)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    def _draw_badge(self, draw: ImageDraw.ImageDraw, color_rgb: Tuple[int, int, int]) -> None:
        """Draw agent badge with DQ score at top-left."""
        font = _get_font(14)
        badge_text = self._config.agent.upper()
        if self._config.dq_score is not None:
            badge_text += f"  DQ {self._config.dq_score:.0f}/5"

        bbox = font.getbbox(badge_text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = BADGE_MARGIN
        y = TOP_BAR_HEIGHT + BADGE_MARGIN
        bg_rect = [
            (x, y),
            (x + text_w + BADGE_PADDING_X * 2, y + text_h + BADGE_PADDING_Y * 2),
        ]
        draw.rectangle(bg_rect, fill=(0, 0, 0, 160))
        draw.text(
            (x + BADGE_PADDING_X, y + BADGE_PADDING_Y),
            badge_text,
            fill=(*color_rgb, 255),
            font=font,
        )

    def _draw_logo(self, draw: ImageDraw.ImageDraw, width: int) -> None:
        """Draw Sinal· text logo at top-right."""
        font = _get_font(16)
        logo_text = "Sinal\u00b7"

        bbox = font.getbbox(logo_text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = width - BADGE_MARGIN - text_w - BADGE_PADDING_X * 2
        y = TOP_BAR_HEIGHT + BADGE_MARGIN
        bg_rect = [
            (x, y),
            (x + text_w + BADGE_PADDING_X * 2, y + text_h + BADGE_PADDING_Y * 2),
        ]
        draw.rectangle(bg_rect, fill=(0, 0, 0, 160))
        draw.text(
            (x + BADGE_PADDING_X, y + BADGE_PADDING_Y),
            logo_text,
            fill=(255, 255, 255, 255),
            font=font,
        )

    def _draw_gradient(self, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        """Draw bottom gradient fade for legibility."""
        start_y = height - GRADIENT_HEIGHT
        for i in range(GRADIENT_HEIGHT):
            alpha = int(180 * (i / GRADIENT_HEIGHT))
            draw.line([(0, start_y + i), (width, start_y + i)], fill=(0, 0, 0, alpha))

    def _draw_url(self, draw: ImageDraw.ImageDraw, height: int) -> None:
        """Draw sinal.tech URL at bottom-left."""
        font = _get_font(12)
        draw.text(
            (BADGE_MARGIN, height - BADGE_MARGIN - 14),
            "sinal.tech",
            fill=(255, 255, 255, 200),
            font=font,
        )

    def _draw_mini_bar(self, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        """Draw mini 5-color bar at bottom-right."""
        total_w = len(MINI_BAR_COLORS) * MINI_BAR_SEGMENT_WIDTH
        start_x = width - MINI_BAR_MARGIN - total_w
        y = height - MINI_BAR_MARGIN - MINI_BAR_HEIGHT

        for i, color_hex in enumerate(MINI_BAR_COLORS):
            rgb = _hex_to_rgb(color_hex)
            x = start_x + i * MINI_BAR_SEGMENT_WIDTH
            draw.rectangle(
                [(x, y), (x + MINI_BAR_SEGMENT_WIDTH, y + MINI_BAR_HEIGHT)],
                fill=(*rgb, 255),
            )


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a font at the given size, falling back to Pillow default."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Pillow < 10.1 doesn't support size parameter
        return ImageFont.load_default()
