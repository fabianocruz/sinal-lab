#!/usr/bin/env python3
"""Safely reset the database by removing all agent-generated data.

Admin-created content (ARTICLE content_type or rows with no agent provenance)
is always preserved.

Usage:
    # Preview what would be deleted (no writes)
    python scripts/reset_production.py --dry-run

    # Execute the reset (requires explicit confirmation flag)
    python scripts/reset_production.py --confirm

    # Verbose output during execution
    python scripts/reset_production.py --confirm --verbose

    # Production via Railway CLI
    railway run python scripts/reset_production.py --dry-run

Exit codes:
    0  success (or dry-run preview completed)
    1  error (database connection failure, unexpected exception)
    2  aborted by user (neither --dry-run nor --confirm passed)
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Make all packages.* and apps.* imports resolvable regardless of cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [reset_production] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("reset_production")


# ---------------------------------------------------------------------------
# Table existence check
# ---------------------------------------------------------------------------


def table_exists(session: Session, table_name: str) -> bool:
    """Return True if the table exists in the current PostgreSQL schema.

    Uses information_schema so it works against any PostgreSQL version
    without relying on pg_catalog internals.
    """
    result = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
            LIMIT 1
            """
        ),
        {"table_name": table_name},
    ).fetchone()
    return result is not None


# ---------------------------------------------------------------------------
# Row counting helpers
# ---------------------------------------------------------------------------


def count_evidence_items(session: Session) -> int:
    row = session.execute(text("SELECT COUNT(*) FROM evidence_items")).fetchone()
    return int(row[0]) if row else 0


def count_agent_runs(session: Session) -> int:
    row = session.execute(text("SELECT COUNT(*) FROM agent_runs")).fetchone()
    return int(row[0]) if row else 0


def count_funding_rounds(session: Session) -> int:
    row = session.execute(text("SELECT COUNT(*) FROM funding_rounds")).fetchone()
    return int(row[0]) if row else 0


def count_agent_content(session: Session) -> int:
    """Count content_pieces rows that are agent-generated (will be deleted)."""
    row = session.execute(
        text(
            "SELECT COUNT(*) FROM content_pieces WHERE agent_name IS NOT NULL"
        )
    ).fetchone()
    return int(row[0]) if row else 0


def fetch_preserved_content(
    session: Session,
) -> List[Tuple[str, str]]:
    """Return (title, slug) for all content_pieces that will be preserved.

    Preserved rows are those that satisfy either condition:
      - content_type = 'ARTICLE'
      - agent_name IS NULL AND agent_run_id IS NULL
    """
    rows = session.execute(
        text(
            """
            SELECT title, slug
            FROM content_pieces
            WHERE content_type = 'ARTICLE'
               OR (agent_name IS NULL AND agent_run_id IS NULL)
            ORDER BY title
            """
        )
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Dry-run preview
# ---------------------------------------------------------------------------


def print_dry_run_report(
    session: Session,
    logger: logging.Logger,
    has_agent_runs: bool,
    has_funding_rounds: bool,
) -> None:
    """Print a human-readable preview of what would be deleted."""
    n_evidence = count_evidence_items(session)
    n_agent_runs = count_agent_runs(session) if has_agent_runs else 0
    n_funding = count_funding_rounds(session) if has_funding_rounds else 0
    n_agent_content = count_agent_content(session)
    preserved = fetch_preserved_content(session)
    n_preserved = len(preserved)

    print("")
    print("DRY RUN -- would delete:")
    print(f"  evidence_items:  {n_evidence:,} rows")

    if has_agent_runs:
        print(f"  agent_runs:      {n_agent_runs:,} rows")
    else:
        print("  agent_runs:      (table does not exist -- skipped)")

    if has_funding_rounds:
        print(f"  funding_rounds:  {n_funding:,} rows")
    else:
        print("  funding_rounds:  (table does not exist -- skipped)")

    preserved_label = (
        f"preserving {n_preserved} admin article{'s' if n_preserved != 1 else ''}"
        if n_preserved
        else "no admin articles to preserve"
    )
    print(f"  content_pieces:  {n_agent_content:,} rows ({preserved_label})")
    print("")

    if preserved:
        print("Preserved content:")
        for title, slug in preserved:
            print(f'  - "{title}" (slug: {slug})')
        print("")

    logger.debug(
        "dry_run counts: evidence=%d agent_runs=%d funding_rounds=%d "
        "agent_content=%d preserved=%d",
        n_evidence,
        n_agent_runs,
        n_funding,
        n_agent_content,
        n_preserved,
    )


# ---------------------------------------------------------------------------
# Actual deletion (wrapped in a single transaction)
# ---------------------------------------------------------------------------


def execute_reset(
    session: Session,
    logger: logging.Logger,
    has_agent_runs: bool,
    has_funding_rounds: bool,
) -> None:
    """Delete all agent-generated data in FK-safe order within one transaction.

    Deletion order:
      1. evidence_items    — raw data items, no FK deps on other tables
      2. agent_runs        — run metadata, no FK deps on other tables
      3. funding_rounds    — domain-specific persist from FUNDING agent
      4. content_pieces    — agent-generated rows only (agent_name IS NOT NULL)

    If any statement fails the entire transaction is rolled back and the
    exception is re-raised for the caller to handle.
    """
    try:
        # 1. evidence_items (always exists)
        result = session.execute(text("DELETE FROM evidence_items"))
        n_evidence = result.rowcount
        logger.info("Deleted %d rows from evidence_items", n_evidence)

        # 2. agent_runs (may not exist in all environments)
        n_agent_runs = 0
        if has_agent_runs:
            result = session.execute(text("DELETE FROM agent_runs"))
            n_agent_runs = result.rowcount
            logger.info("Deleted %d rows from agent_runs", n_agent_runs)
        else:
            logger.debug("agent_runs table not found -- skipped")

        # 3. funding_rounds (may not exist in all environments)
        n_funding = 0
        if has_funding_rounds:
            result = session.execute(text("DELETE FROM funding_rounds"))
            n_funding = result.rowcount
            logger.info("Deleted %d rows from funding_rounds", n_funding)
        else:
            logger.debug("funding_rounds table not found -- skipped")

        # 4. content_pieces — agent-generated only
        result = session.execute(
            text("DELETE FROM content_pieces WHERE agent_name IS NOT NULL")
        )
        n_content = result.rowcount
        logger.info("Deleted %d rows from content_pieces (agent-generated)", n_content)

        # Commit once — all-or-nothing
        session.commit()

        # Summary
        print("")
        print("Reset complete:")
        print(f"  evidence_items deleted:  {n_evidence:,}")
        if has_agent_runs:
            print(f"  agent_runs deleted:      {n_agent_runs:,}")
        else:
            print("  agent_runs:              (table did not exist)")
        if has_funding_rounds:
            print(f"  funding_rounds deleted:  {n_funding:,}")
        else:
            print("  funding_rounds:          (table did not exist)")
        print(f"  content_pieces deleted:  {n_content:,} (agent-generated only)")
        print("")

    except Exception:
        session.rollback()
        logger.error("Reset failed -- all changes rolled back")
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely reset the database by removing all agent-generated data. "
            "Admin-created articles (content_type='ARTICLE' or rows with no "
            "agent provenance) are always preserved."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview only — no writes
  python scripts/reset_production.py --dry-run

  # Execute the reset
  python scripts/reset_production.py --confirm

  # Production (via Railway CLI)
  railway run python scripts/reset_production.py --confirm --verbose
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print row counts per table without deleting anything.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Execute the deletion. Required to prevent accidental runs.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Require at least one of --dry-run or --confirm.
    if not args.dry_run and not args.confirm:
        print(__doc__)
        print("ERROR: pass --dry-run to preview or --confirm to execute.")
        sys.exit(2)

    logger = setup_logging(args.verbose)

    # Show target database (mask credentials for safety).
    db_display = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info("Target database: %s", db_display)

    # Build a throw-away engine scoped to this script run.
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    ScriptSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session: Optional[Session] = None
    try:
        session = ScriptSession()

        # Probe optional tables so the rest of the script can branch safely.
        has_agent_runs = table_exists(session, "agent_runs")
        has_funding_rounds = table_exists(session, "funding_rounds")

        logger.debug(
            "Table probe: agent_runs=%s funding_rounds=%s",
            has_agent_runs,
            has_funding_rounds,
        )

        if args.dry_run:
            print_dry_run_report(session, logger, has_agent_runs, has_funding_rounds)
        else:
            # --confirm path: show preserved content first, then delete.
            preserved = fetch_preserved_content(session)
            if preserved:
                print("")
                print("The following admin content will be PRESERVED:")
                for title, slug in preserved:
                    print(f'  - "{title}" (slug: {slug})')
                print("")

            execute_reset(session, logger, has_agent_runs, has_funding_rounds)

    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if session is not None:
            session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
