"""Custom CLI entry point for the Feed Curator agent.

Unlike other agents that use run_agent_cli with a period_arg (week/edition),
the Feed Curator has no period concept. It runs on-demand or every 4 hours,
curating the most recent signals.

Usage:
    python -m apps.agents.feed_curator.main --dry-run --verbose
    python -m apps.agents.feed_curator.main --persist
    python -m apps.agents.feed_curator.main --persist --limit 50
    python -m apps.agents.feed_curator.main --dry-run --limit 30 --output-limit 10
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from apps.agents.feed_curator.agent import FeedCuratorAgent
from apps.agents.feed_curator.config import FEED_CURATOR_CONFIG

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().setLevel(level)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FEED_CURATOR — Sinal.lab Feed Curator Agent (Ana Torres)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Save curated items to the database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving output",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=FEED_CURATOR_CONFIG.default_input_limit,
        help=f"Max signals to load from DB (default: {FEED_CURATOR_CONFIG.default_input_limit})",
    )
    parser.add_argument(
        "--output-limit",
        type=int,
        default=FEED_CURATOR_CONFIG.default_output_limit,
        help=f"Max curated items to produce (default: {FEED_CURATOR_CONFIG.default_output_limit})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save the Markdown output",
    )
    parser.add_argument(
        "--no-thumbnails",
        action="store_true",
        help="Skip og:image thumbnail fetching (faster)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger.info("Starting Feed Curator agent (limit=%d, output_limit=%d)", args.limit, args.output_limit)

    # Create agent
    agent = FeedCuratorAgent(
        persist=args.persist,
        input_limit=args.limit,
        output_limit=args.output_limit,
        fetch_thumbnails=not args.no_thumbnails,
    )

    # Set up DB session (needed to load signals)
    from packages.database.session import get_session

    session = get_session()
    agent.set_db_session(session)

    try:
        result = agent.run()

        # Validate
        errors = result.validate()
        if errors:
            logger.warning("Output validation issues: %s", errors)

        metadata = agent.get_run_metadata()
        logger.info("Run metadata: %s", metadata)
        logger.info("Confidence: %s", result.confidence.to_dict())

        # Dry run
        if args.dry_run:
            logger.info("Dry run complete")
            print("\n" + "=" * 60)
            md = result.to_markdown()
            print(md[:3000])
            if len(md) > 3000:
                print(f"... ({len(md)} total chars)")
            print("=" * 60)
            return

        # Write Markdown output
        output_dir = str(PROJECT_ROOT / "apps" / "agents" / "feed_curator" / "output")
        output_path = args.output or os.path.join(output_dir, f"feed-curated-{agent.run_id}.md")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        md_content = result.to_markdown()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info("Markdown saved to %s", output_path)

        # Persist to database
        if args.persist:
            logger.info("Persisting curated items to database...")
            from apps.agents.base.persistence import persist_agent_output
            from apps.agents.feed_curator.db_writer import persist_curated_feed

            persist_agent_output(
                session, agent, result,
                slug=f"feed-curated-{agent.run_id}",
            )
            persist_curated_feed(agent, result, session)
            session.commit()
            logger.info("Feed Curator data committed to database")

        # Summary
        curated_count = len(agent._curated_items)
        print(f"\nFEED_CURATOR Report generated successfully!")
        print(f"  Input signals: {len(agent._raw_signals)}")
        print(f"  Curated items: {curated_count}")
        print(
            f"  Confidence: {result.confidence.grade} "
            f"(DQ: {result.confidence.dq_display}/5, "
            f"AC: {result.confidence.ac_display}/5)"
        )
        print(f"  Output: {output_path}")
        if args.persist:
            print("  DB: persisted")

    finally:
        session.close()


if __name__ == "__main__":
    main()
