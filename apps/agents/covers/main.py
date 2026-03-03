"""CLI entry point for cover image generation.

Usage:
    python -m apps.agents.covers.main \\
        --headline "Nubank testa agentes de AI" \\
        --lede "O maior banco digital da LATAM iniciou testes" \\
        --agent radar \\
        --edition 30 \\
        --dq-score 4.0 \\
        --variations 3 \\
        --open
"""

import argparse
import logging
import sys
import webbrowser

from apps.agents.covers.pipeline import CoverPipeline
from apps.agents.covers.prompt_generator import CoverBriefing

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI args, run the cover pipeline, and print results."""
    parser = argparse.ArgumentParser(
        description="Generate AI editorial cover images for Sinal publications."
    )
    parser.add_argument("--headline", required=True, help="Article headline")
    parser.add_argument("--lede", required=True, help="Article lede/summary")
    parser.add_argument(
        "--agent", required=True,
        choices=["radar", "funding", "codigo", "mercado", "sintese"],
        help="Agent name (determines accent color)",
    )
    parser.add_argument("--edition", type=int, required=True, help="Edition number")
    parser.add_argument("--dq-score", type=float, default=None, help="Data quality score (0-5)")
    parser.add_argument("--variations", type=int, default=3, choices=[1, 2, 3], help="Number of variations")
    parser.add_argument("--open", action="store_true", help="Open generated images in browser")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    briefing = CoverBriefing(
        headline=args.headline,
        lede=args.lede,
        agent=args.agent,
        edition=args.edition,
        dq_score=args.dq_score,
    )

    pipeline = CoverPipeline()
    result = pipeline.run(briefing, variations=args.variations)

    if result.errors:
        for error in result.errors:
            logger.warning("Pipeline error: %s", error)

    if not result.images:
        print("No images generated. Check errors above.", file=sys.stderr)
        sys.exit(1)

    print(f"\nGenerated {len(result.images)} cover image(s):\n")
    print(f"Prompt used: {result.prompt_used}\n")
    for img in result.images:
        print(f"  Variation {img['variation']}: {img['url']}")

    if args.open:
        for img in result.images:
            webbrowser.open(img["url"])


if __name__ == "__main__":
    main()
