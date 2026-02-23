#!/usr/bin/env python3
"""Batch-generate content for all 5 agents across N editions.

Runs sintese, radar, codigo, funding, and mercado sequentially for each
edition, using the orchestrator in-process. Idempotent: skips any slug
that already exists in the database. After all editions complete,
promotes all "approved" pieces to "published" with computed dates.

Usage:
    # Generate 30 editions starting from edition 19, week 1
    python scripts/batch_generate.py

    # Custom range
    python scripts/batch_generate.py --editions 10 --start-edition 40 --start-week 10

    # Preview without writing to DB
    python scripts/batch_generate.py --dry-run

    # Skip editorial review
    python scripts/batch_generate.py --no-editorial --no-evidence

    # Verbose logging
    python scripts/batch_generate.py --verbose
"""

import argparse
import logging
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Import shared infrastructure from run_agents.py
from scripts.run_agents import (  # noqa: E402
    AGENTS,
    DOMAIN_PERSIST_FNS,
    _load_agent_class,
    orchestrate_single_agent,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Agents to run in order (index is intentionally excluded — data-only agent)
BATCH_AGENTS: List[str] = ["sintese", "radar", "codigo", "funding", "mercado"]

# Base publication date: editions are spaced one week apart.
# Edition #1 maps to this anchor; edition N maps to anchor + (N-1) weeks.
_PUB_ANCHOR = datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_week(start_week: int, edition_index: int) -> int:
    """Return the ISO-style week number for a given edition index.

    Wraps at 52 so results stay in [1, 52].

    Args:
        start_week: Week number of the first edition (1-52).
        edition_index: Zero-based offset from the first edition.

    Returns:
        Week number in range [1, 52].
    """
    return ((start_week - 1 + edition_index) % 52) + 1


def _compute_published_at(start_edition: int, edition_number: int) -> datetime:
    """Map an edition number to a publication timestamp.

    Editions are spaced exactly one week apart from the anchor date.
    Edition start_edition → anchor; edition start_edition+1 → anchor + 7d; etc.

    Args:
        start_edition: Edition number that maps to the anchor date.
        edition_number: The edition whose date is being computed.

    Returns:
        UTC datetime for the edition.
    """
    offset_weeks = edition_number - start_edition
    return _PUB_ANCHOR + timedelta(weeks=offset_weeks)


def _slug_exists(session: object, slug: str) -> bool:
    """Return True if a ContentPiece with this slug already exists.

    Args:
        session: SQLAlchemy session.
        slug: The slug to look up.

    Returns:
        True if the slug is already in the database.
    """
    from packages.database.models.content_piece import ContentPiece

    result = session.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    return result is not None


def _publish_approved_pieces(
    session: object,
    start_edition: int,
    start_week: int,
    editions: int,
    dry_run: bool,
) -> int:
    """Promote all "approved" ContentPieces to "published" with computed dates.

    Iterates over every edition and agent, finds matching slugs with
    review_status="approved", and updates them. The published_at date is
    computed from the edition number for sintese pieces, and from the week
    number for all other agents.

    Args:
        session: SQLAlchemy session.
        start_edition: First edition number in the batch.
        start_week: Week number of the first edition.
        editions: Total number of editions.
        dry_run: If True, log what would happen without writing.

    Returns:
        Number of pieces promoted to published.
    """
    from packages.database.models.content_piece import ContentPiece

    logger = logging.getLogger("batch_generate")
    promoted = 0

    for edition_index in range(editions):
        edition_number = start_edition + edition_index
        week_number = _compute_week(start_week, edition_index)

        for agent_name in BATCH_AGENTS:
            cfg = AGENTS[agent_name]
            period_value = (
                edition_number if cfg["period_arg"] == "edition" else week_number
            )
            slug = cfg["slug_pattern"].format(period=period_value)
            pub_date = _compute_published_at(start_edition, edition_number)

            piece = (
                session.query(ContentPiece)
                .filter(
                    ContentPiece.slug == slug,
                    ContentPiece.review_status == "approved",
                )
                .first()
            )

            if piece is None:
                continue

            if dry_run:
                logger.info(
                    "[dry-run] Would publish %s → published_at=%s",
                    slug,
                    pub_date.isoformat(),
                )
            else:
                piece.review_status = "published"
                piece.published_at = pub_date
                logger.debug("Published %s at %s", slug, pub_date.isoformat())

            promoted += 1

    if not dry_run and promoted > 0:
        session.commit()
        logger.info("Committed %d published pieces to database", promoted)

    return promoted


# ---------------------------------------------------------------------------
# Core batch loop
# ---------------------------------------------------------------------------


def run_batch(
    editions: int,
    start_edition: int,
    start_week: int,
    enable_editorial: bool,
    enable_evidence: bool,
    dry_run: bool,
    verbose: bool,
) -> Tuple[int, int]:
    """Run all batch agents for every edition in the requested range.

    Args:
        editions: Number of editions to generate.
        start_edition: First edition number (sintese uses this directly).
        start_week: Week number for the first edition (wraps at 52).
        enable_editorial: Whether to run editorial review in orchestrator.
        enable_evidence: Whether to persist evidence items.
        dry_run: If True, skip all database writes.
        verbose: Whether verbose logging is active (used for progress labels).

    Returns:
        Tuple of (successes, failures) across all agent runs.
    """
    from packages.database.session import get_session

    logger = logging.getLogger("batch_generate")

    total_runs = editions * len(BATCH_AGENTS)
    successes = 0
    failures = 0
    run_counter = 0

    session = get_session()
    try:
        for edition_index in range(editions):
            edition_number = start_edition + edition_index
            week_number = _compute_week(start_week, edition_index)
            edition_results: Dict[str, str] = {}

            for agent_name in BATCH_AGENTS:
                run_counter += 1
                cfg = AGENTS[agent_name]
                period_value = (
                    edition_number
                    if cfg["period_arg"] == "edition"
                    else week_number
                )
                slug = cfg["slug_pattern"].format(period=period_value)

                # Idempotency check — skip if already generated
                if _slug_exists(session, slug):
                    logger.debug("Skipping %s (already exists)", slug)
                    edition_results[agent_name] = "skip"
                    successes += 1
                    continue

                if dry_run:
                    logger.info(
                        "[dry-run] Would run %s (slug=%s, period=%d)",
                        agent_name.upper(),
                        slug,
                        period_value,
                    )
                    edition_results[agent_name] = "dry-run"
                    successes += 1
                    continue

                exit_code = orchestrate_single_agent(
                    agent_name,
                    period_value=period_value,
                    session=session,
                    enable_editorial=enable_editorial,
                    enable_evidence=enable_evidence,
                )

                if exit_code == 0:
                    edition_results[agent_name] = "ok"
                    successes += 1
                else:
                    edition_results[agent_name] = "FAIL"
                    failures += 1

            # Per-edition progress log
            results_str = ", ".join(
                "{} {}".format(name.upper(), status)
                for name, status in edition_results.items()
            )
            logger.info(
                "[%d/%d] Edition #%d, week %d: %s",
                run_counter,
                total_runs,
                edition_number,
                week_number,
                results_str,
            )

        # Promote approved pieces to published
        if not dry_run:
            promoted = _publish_approved_pieces(
                session,
                start_edition=start_edition,
                start_week=start_week,
                editions=editions,
                dry_run=False,
            )
            logger.info("Promoted %d approved pieces to published", promoted)
        else:
            promoted = _publish_approved_pieces(
                session,
                start_edition=start_edition,
                start_week=start_week,
                editions=editions,
                dry_run=True,
            )
            logger.info(
                "[dry-run] Would promote %d approved pieces to published", promoted
            )

    finally:
        session.close()

    return successes, failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-generate agent content for N editions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Agents run per edition (in order):
  sintese   uses edition number   → slug: sinal-semanal-{edition}
  radar     uses week number      → slug: radar-week-{week}
  codigo    uses week number      → slug: codigo-week-{week}
  funding   uses week number      → slug: funding-semanal-{week}
  mercado   uses week number      → slug: mercado-week-{week}

Week numbers wrap at 52 (ISO calendar).
Existing slugs are skipped (idempotent).
After all editions, approved pieces are promoted to published.
        """,
    )
    parser.add_argument(
        "--editions",
        type=int,
        default=30,
        metavar="N",
        help="Number of editions to generate (default: 30)",
    )
    parser.add_argument(
        "--start-edition",
        type=int,
        default=19,
        metavar="M",
        dest="start_edition",
        help="First edition number (default: 19)",
    )
    parser.add_argument(
        "--start-week",
        type=int,
        default=1,
        metavar="W",
        dest="start_week",
        help="Week number for the first edition, wraps at 52 (default: 1)",
    )
    parser.add_argument(
        "--no-editorial",
        action="store_true",
        dest="no_editorial",
        help="Skip editorial review in orchestrator",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        dest="no_evidence",
        help="Skip evidence item persistence in orchestrator",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview all runs without writing to the database",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("batch_generate")

    logger.info(
        "Starting batch: %d editions, start_edition=%d, start_week=%d, "
        "editorial=%s, evidence=%s, dry_run=%s",
        args.editions,
        args.start_edition,
        args.start_week,
        not args.no_editorial,
        not args.no_evidence,
        args.dry_run,
    )

    successes, failures = run_batch(
        editions=args.editions,
        start_edition=args.start_edition,
        start_week=args.start_week,
        enable_editorial=not args.no_editorial,
        enable_evidence=not args.no_evidence,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    total = successes + failures
    logger.info("=" * 50)
    logger.info(
        "Batch complete: %d/%d runs succeeded, %d failed",
        successes,
        total,
        failures,
    )

    if failures:
        logger.error("%d run(s) failed — check logs above for details", failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
