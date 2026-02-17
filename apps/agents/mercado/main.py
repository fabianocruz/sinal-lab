"""CLI entry point for MERCADO agent."""

import argparse
import logging
import sys
from datetime import datetime

from apps.agents.mercado.agent import MercadoAgent
from apps.agents.mercado.db_writer import persist_all_profiles
from packages.database.session import get_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MERCADO Agent — LATAM startup mapping and ecosystem intelligence"
    )
    parser.add_argument(
        "--week",
        type=int,
        default=datetime.now().isocalendar()[1],
        help="Week number of the year (1-52). Defaults to current week.",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Save results to database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving or persisting (preview only)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for Markdown report",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("MERCADO Agent — LATAM Startup Mapping")
    logger.info("Week: %d", args.week)
    logger.info("Persist: %s", args.persist)
    logger.info("Dry run: %s", args.dry_run)
    logger.info("=" * 80)

    try:
        # Initialize and run agent
        agent = MercadoAgent(week_number=args.week)
        result = agent.run()

        # Display output
        logger.info("\n" + "=" * 80)
        logger.info("MERCADO Report Generated")
        logger.info("=" * 80)
        print(result.body_md)
        logger.info("=" * 80)
        logger.info("Confidence: %s (DQ: %.2f, AC: %.2f)",
                    result.confidence.grade,
                    result.confidence.data_quality,
                    result.confidence.analysis_confidence)
        logger.info("Sources: %d", len(result.sources))
        logger.info("=" * 80)

        # Save to file if requested
        if args.output and not args.dry_run:
            with open(args.output, "w", encoding="utf-8") as f:
                # Write with YAML frontmatter
                f.write("---\n")
                f.write(f"title: \"{result.title}\"\n")
                f.write(f"agent: {result.agent_name}\n")
                f.write(f"run_id: \"{result.run_id}\"\n")
                f.write(f"generated_at: \"{datetime.now().isoformat()}\"\n")
                f.write(f"content_type: {result.content_type}\n")
                f.write(f"confidence_dq: {result.confidence.data_quality:.2f}\n")
                f.write(f"confidence_ac: {result.confidence.analysis_confidence:.2f}\n")
                f.write(f"confidence_grade: {result.confidence.grade}\n")
                f.write(f"source_count: {len(result.sources)}\n")
                f.write("sources:\n")
                for source in result.sources[:10]:
                    f.write(f"  - \"{source}\"\n")
                f.write("---\n\n")
                f.write(result.body_md)

            logger.info("Report saved to: %s", args.output)

        # Persist to database if requested
        if args.persist and not args.dry_run:
            logger.info("Persisting to database...")

            # Get scored profiles from agent
            scored_profiles = agent.score(agent.process(agent.collect()))

            # Convert to (CompanyProfile, confidence) tuples
            profiles_with_confidence = [
                (scored.profile, scored.composite_score)
                for scored in scored_profiles
            ]

            # Persist
            session = get_session()
            try:
                stats = persist_all_profiles(session, profiles_with_confidence)
                logger.info("Persistence stats: %s", stats)
            finally:
                session.close()

        logger.info("MERCADO agent run complete!")
        return 0

    except Exception as e:
        logger.error("MERCADO agent failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
