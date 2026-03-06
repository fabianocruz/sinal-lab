"""Test article cover generation end-to-end (saves locally, no upload).

Usage:
    python3 scripts/test_article_covers.py
    python3 scripts/test_article_covers.py --prompt-only   # just show prompts
"""

import argparse
import io
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from apps.agents.covers.config import ARTICLE_BADGE_TEXT, ARTICLE_COLOR  # noqa: E402
from apps.agents.covers.overlay import BrandOverlay, OverlayConfig  # noqa: E402
from apps.agents.covers.prompt_generator import (  # noqa: E402
    ArticleBriefing,
    CoverPromptGenerator,
)
from apps.agents.covers.recraft import RecraftClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ARTICLES = [
    ArticleBriefing(
        title="6 PRs para colocar um site no ar",
        thesis="A jornada de construir infra do zero, do repo vazio ao deploy",
        article_type="diary",
        mood="progression, building",
        author="Fabiano Cruz",
    ),
    ArticleBriefing(
        title="Confiança não escala com marketing",
        thesis="A diferença entre parecer confiável e ser confiável em tech",
        article_type="essay",
        author="Fabiano Cruz",
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--variations", type=int, default=1)
    args = parser.parse_args()

    output_dir = _PROJECT_ROOT / "output" / "covers" / "artigos"
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_gen = CoverPromptGenerator()
    if not prompt_gen.is_available:
        logger.error("LLM client unavailable (ANTHROPIC_API_KEY not set?)")
        sys.exit(1)

    recraft = RecraftClient()

    for article in ARTICLES:
        slug = article.title.lower().replace(" ", "-")[:40]
        logger.info(f"\n{'='*60}")
        logger.info(f"ARTICLE: {article.title}")
        logger.info(f"TYPE: {article.article_type}")
        logger.info(f"{'='*60}")

        # Stage 1: Generate prompt
        prompt = prompt_gen.generate_article_prompt(article)
        if not prompt:
            logger.error("  Prompt generation failed")
            continue

        logger.info(f"\nPROMPT:\n{prompt}\n")

        if args.prompt_only:
            continue

        # Stage 2: Generate image(s)
        if not recraft.is_available:
            logger.error("  Recraft unavailable (RECRAFT_API_KEY not set?)")
            continue

        images = recraft.generate(prompt, variations=args.variations)
        if not images:
            logger.error("  Image generation failed")
            continue

        # Stage 3: Apply overlay + save
        overlay = BrandOverlay(OverlayConfig(
            agent=ARTICLE_BADGE_TEXT,
            agent_color=ARTICLE_COLOR,
            is_article=True,
            author=article.author,
        ))

        for img in images:
            composited = overlay.apply(img.image_bytes)
            out_path = output_dir / f"{slug}-v{img.variation}.png"
            out_path.write_bytes(composited)
            logger.info(f"  SAVED: {out_path}")

    logger.info(f"\nDone. Check: {output_dir}/")


if __name__ == "__main__":
    main()
