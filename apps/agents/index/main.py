"""CLI entry point for INDEX agent.

Usage:
    python -m apps.agents.index.main --dry-run
    python -m apps.agents.index.main --persist --rf-file /path/to/cnpj.csv
    python -m apps.agents.index.main --api-only --persist
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.agents.index.agent import IndexAgent

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI arguments and run the INDEX agent pipeline."""
    parser = argparse.ArgumentParser(
        description="INDEX agent — LATAM Startup Index seed pipeline",
    )
    parser.add_argument("--week", type=int, default=0, help="Week number (unused, for CLI compat)")
    parser.add_argument("--rf-file", type=str, default=None, help="Path to Receita Federal CSV file")
    parser.add_argument("--api-only", action="store_true", help="Skip file-based sources")
    parser.add_argument("--persist", action="store_true", help="Persist results to database")
    parser.add_argument("--output", type=str, default=None, help="Save Markdown output to file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    agent = IndexAgent(
        week_number=args.week,
        rf_file=args.rf_file,
        api_only=args.api_only,
    )

    result = agent.run()

    # Print summary
    print(f"\n{'='*60}")
    print(f"INDEX Agent Run Complete: {result.title}")
    print(f"Confidence: {result.confidence.grade} (DQ={result.confidence.data_quality:.2f}, AC={result.confidence.analysis_confidence:.2f})")
    print(f"Sources: {len(result.sources)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("[DRY RUN] Results not persisted.")
        print(result.to_markdown()[:2000])
        return

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.to_markdown())
        print(f"Output saved to: {output_path}")

    if args.persist:
        try:
            from packages.database.session import get_session
            from apps.agents.index.db_writer import persist_index_results
            from apps.agents.base.persistence import persist_agent_run

            session = get_session()
            try:
                # Persist agent run metadata
                persist_agent_run(session, agent, result)

                # Persist companies
                stats = persist_index_results(session, agent._scored_companies)
                session.commit()
                print(f"Persisted: {stats}")
            finally:
                session.close()
        except Exception as e:
            logger.error("Persistence failed: %s", e, exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
