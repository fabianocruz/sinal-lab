#!/usr/bin/env python3
"""One-time bulk seed script for the LATAM Startup Index.

Collects data from all configured INDEX sources, runs the dedup pipeline,
and loads results into the Company table.

Usage:
    # Preview collection + dedup stats (no persistence)
    python scripts/seed_index.py --dry-run

    # API-only sources (no RF file needed)
    python scripts/seed_index.py --api-only --dry-run

    # Full seed with Receita Federal CSV
    python scripts/seed_index.py --rf-file /path/to/estabelecimentos.csv

    # API-only, persist to database
    python scripts/seed_index.py --api-only
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("seed_index")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the LATAM Startup Index from bulk data sources",
    )
    parser.add_argument("--rf-file", type=str, default=None, help="Path to Receita Federal CSV file")
    parser.add_argument("--api-only", action="store_true", help="Skip file-based sources (RF, Crunchbase CSV)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without persisting to database")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.info("Starting INDEX seed pipeline")
    logger.info("  RF file: %s", args.rf_file or "(none)")
    logger.info("  API only: %s", args.api_only)
    logger.info("  Dry run: %s", args.dry_run)

    # Run the INDEX agent
    from apps.agents.index.agent import IndexAgent

    agent = IndexAgent(
        rf_file=args.rf_file,
        api_only=args.api_only,
    )

    try:
        result = agent.run()
    except Exception as e:
        logger.error("INDEX agent run failed: %s", e, exc_info=True)
        return 1

    # Print summary
    scored = agent._scored_companies
    sources = agent._sources_used

    print(f"\n{'='*60}")
    print(f"INDEX Seed Pipeline Complete")
    print(f"{'='*60}")
    print(f"  Companies found:   {len(scored)}")
    print(f"  Sources used:      {', '.join(sources)}")
    print(f"  Confidence grade:  {result.confidence.grade}")
    print(f"  New companies:     {sum(1 for m, _ in scored if m.is_new)}")
    print(f"  Existing matches:  {sum(1 for m, _ in scored if not m.is_new)}")

    if scored:
        avg_score = sum(s for _, s in scored) / len(scored)
        print(f"  Average score:     {avg_score:.3f}")
        print(f"  Top company:       {scored[0][0].name} ({scored[0][1]:.3f})")

    # Source breakdown
    source_counts: dict[str, int] = {}
    for merged, _ in scored:
        for source in merged.sources:
            source_counts[source] = source_counts.get(source, 0) + 1

    if source_counts:
        print(f"\n  Source breakdown:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {source}: {count}")

    # Multi-source stats
    multi = sum(1 for m, _ in scored if m.source_count >= 2)
    print(f"\n  Multi-source:      {multi}/{len(scored)} ({multi/len(scored)*100:.1f}%)" if scored else "")

    print(f"{'='*60}\n")

    if args.dry_run:
        print("[DRY RUN] Results not persisted to database.")
        return 0

    # Persist to database
    try:
        from packages.database.session import get_session
        from apps.agents.index.db_writer import persist_index_results
        from apps.agents.base.persistence import persist_agent_run

        session = get_session()
        try:
            # Persist agent run
            persist_agent_run(session, agent, result)

            # Persist companies
            stats = persist_index_results(session, scored)
            session.commit()

            print(f"Persisted to database:")
            print(f"  Inserted: {stats['inserted']}")
            print(f"  Updated:  {stats['updated']}")
            print(f"  Skipped:  {stats['skipped']}")
        finally:
            session.close()
    except Exception as e:
        logger.error("Persistence failed: %s", e, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
