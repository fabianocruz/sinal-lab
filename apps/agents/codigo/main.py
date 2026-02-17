"""CLI entry point for the CODIGO agent.

Usage:
    python -m apps.agents.codigo.main [--week N] [--output PATH] [--dry-run]
    python -m apps.agents.codigo.main --week 8 --persist
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.agents.codigo.agent import CodigoAgent


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CODIGO — Sinal.lab Developer Ecosystem Intelligence Agent"
    )
    parser.add_argument(
        "--week", type=int, default=datetime.now().isocalendar()[1],
        help="Week number (default: current week)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to save the dev ecosystem report Markdown output",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without saving output",
    )
    parser.add_argument(
        "--persist", action="store_true",
        help="Save agent run and content to the database",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("codigo.main")
    logger.info("Starting CODIGO agent, week #%d", args.week)

    # Run the agent
    agent = CodigoAgent(week_number=args.week)
    result = agent.run()

    # Display results
    metadata = agent.get_run_metadata()
    logger.info("Run metadata: %s", metadata)
    logger.info("Confidence: %s", result.confidence.to_dict())
    logger.info("Provenance summary: %s", agent.provenance.summary())

    if args.dry_run:
        logger.info("Dry run — not saving output")
        print("\n" + "=" * 60)
        print(result.to_markdown()[:2000])
        print("..." if len(result.to_markdown()) > 2000 else "")
        print("=" * 60)
        return

    # Save Markdown output
    md_content = result.to_markdown()
    if args.output:
        output_path = args.output
    else:
        os.makedirs("apps/agents/codigo/output", exist_ok=True)
        output_path = f"apps/agents/codigo/output/codigo-week-{args.week}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Markdown saved to %s", output_path)

    # Persist to database (if requested)
    if args.persist:
        logger.info("Persisting to database...")
        # TODO: Implement database persistence similar to SINTESE
        logger.warning("Database persistence not yet implemented for CODIGO")

    print(f"\nCODIGO Developer Report Week #{args.week} generated successfully!")
    print(f"  Signals analyzed: {metadata['items_collected']}")
    print(f"  Signals processed: {metadata['items_processed']}")
    print(f"  Sources: {agent.provenance.summary()['unique_sources']}")
    print(f"  Confidence: {result.confidence.grade} (DQ: {result.confidence.dq_display}/5, AC: {result.confidence.ac_display}/5)")
    print(f"  Output: {output_path}")
    if args.persist:
        print("  DB: persistence skipped (not implemented)")


if __name__ == "__main__":
    main()
