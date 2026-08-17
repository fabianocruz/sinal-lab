"""Refresh the local DB from prod so local diagnostics can be trusted.

This is the mirror of ``sync_local_to_prod.py`` and runs in the opposite,
much safer direction: it only ever reads from prod and only ever writes to
a database on localhost. It refuses to run otherwise.

Why this exists: local drifted two migrations and ~62k signals behind prod,
which made an audit of /feed and /sinais report a four-month outage that had
never happened. Any measurement of data shape has to be made against data
that looks like production.

Schema is NOT copied. Run migrations first so both sides are at the same
revision::

    alembic -c packages/database/alembic.ini upgrade head

Usage::

    python scripts/sync_prod_to_local.py                    # plan only
    python scripts/sync_prod_to_local.py --apply            # replace local
    python scripts/sync_prod_to_local.py --apply --tables social_signals,signal_clusters
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from sqlalchemy import MetaData, Table, create_engine, func, select, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.schema import sort_tables  # noqa: E402

logger = logging.getLogger("sync_prod_to_local")

LOCAL_URL = os.getenv("DATABASE_URL")
PROD_URL = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

#: Hosts we are willing to write to. Anything else aborts the run.
SAFE_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}

#: Tables that carry the intelligence corpus. These are the ones whose row
#: shape and volume change what a local diagnostic concludes.
DEFAULT_TABLES: List[str] = [
    "companies",
    "funding_rounds",
    "content_pieces",
    "monitored_accounts",
    "social_signals",
    "signal_clusters",
    "weekly_pulses",
    "curated_feed_items",
]

#: Rows per INSERT batch. Large enough to keep the TCP proxy busy, small
#: enough that a failure does not roll back an hour of work.
BATCH_SIZE = 1_000


def _assert_is_local(url: str) -> None:
    """Abort unless ``url`` points at a database on this machine.

    The whole point of this script is that it writes; the only thing standing
    between it and production is this check, so it runs before anything else.
    """
    host = (urlparse(url).hostname or "").lower()
    if host not in SAFE_LOCAL_HOSTS:
        raise SystemExit(
            f"REFUSING TO RUN: write target host is {host!r}, not local.\n"
            f"This script only ever writes to {sorted(SAFE_LOCAL_HOSTS)}."
        )


def _assert_same_revision(local: Engine, prod: Engine) -> None:
    """Abort when the two sides are at different Alembic revisions.

    Copying prod rows into an older local schema fails halfway through and
    leaves the local DB in a worse state than the drift we are fixing.
    """
    def _rev(engine: Engine) -> str:
        with engine.connect() as conn:
            try:
                return conn.execute(text("SELECT version_num FROM alembic_version")).scalar() or "?"
            except Exception:
                return "(none)"

    local_rev, prod_rev = _rev(local), _rev(prod)
    if local_rev != prod_rev:
        raise SystemExit(
            f"REFUSING TO RUN: local is at Alembic {local_rev}, prod at {prod_rev}.\n"
            f"Run: alembic -c packages/database/alembic.ini upgrade head"
        )
    logger.info("Both sides at Alembic revision %s", local_rev)


def _count(engine: Engine, table: Table) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(table)).scalar() or 0


def _reflect(prod: Engine, names: List[str]) -> List[Table]:
    """Reflect the requested tables from prod, ordered parents-first.

    Sorting by foreign-key dependency keeps inserts valid without having to
    drop constraints.
    """
    metadata = MetaData()
    tables = []
    for name in names:
        try:
            tables.append(Table(name, metadata, autoload_with=prod))
        except Exception as exc:
            logger.warning("Skipping %s: %s", name, exc)
    return list(sort_tables(tables))


def _insert_batch(local: Engine, table: Table, payload: List[Dict[str, Any]]) -> int:
    """Insert a batch, falling back to row-by-row when the batch is rejected.

    Prod has drifted: it is missing constraints that local still enforces
    (e.g. curated_feed_items lost its FK to social_signals and accumulated
    rows pointing at signals that no longer exist). Those rows cannot be
    represented locally. Skipping them keeps the copy going; the caller
    reports how many were dropped, because a silent skip would make local
    look like a faithful mirror when it is not.
    """
    try:
        with local.begin() as dst:
            dst.execute(table.insert(), payload)
        return 0
    except IntegrityError:
        pass

    skipped = 0
    for row in payload:
        try:
            with local.begin() as dst:
                dst.execute(table.insert(), [row])
        except IntegrityError:
            skipped += 1
    return skipped


def _copy_table(prod: Engine, local: Engine, table: Table) -> tuple:
    """Replace local contents of ``table`` with prod's, in batches.

    Returns ``(copied, skipped)``.
    """
    copied = skipped = 0
    columns = [c.name for c in table.columns]

    with prod.connect().execution_options(stream_results=True) as src:
        result = src.execute(select(table))
        while True:
            rows = result.fetchmany(BATCH_SIZE)
            if not rows:
                break
            payload: List[Dict[str, Any]] = [dict(zip(columns, row)) for row in rows]
            batch_skipped = _insert_batch(local, table, payload)
            skipped += batch_skipped
            copied += len(payload) - batch_skipped
            logger.info("  %s: %s rows", table.name, f"{copied:,}")

    if skipped:
        logger.warning(
            "  %s: SKIPPED %s rows rejected by local constraints that prod no "
            "longer enforces", table.name, f"{skipped:,}"
        )
    return copied, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually replace local data. Without it, only the plan is printed.",
    )
    parser.add_argument(
        "--tables",
        default=",".join(DEFAULT_TABLES),
        help="Comma-separated table names to refresh.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [sync] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not LOCAL_URL:
        raise SystemExit("DATABASE_URL not set")
    if not PROD_URL:
        raise SystemExit("PROD_DATABASE_URL (or DATABASE_PUBLIC_URL) not set")

    _assert_is_local(LOCAL_URL)

    local = create_engine(LOCAL_URL)
    prod = create_engine(PROD_URL, connect_args={"connect_timeout": 30})

    _assert_same_revision(local, prod)

    names = [t.strip() for t in args.tables.split(",") if t.strip()]
    tables = _reflect(prod, names)

    print(f"\n{'table':<24} {'local':>10} {'prod':>10}")
    print("-" * 48)
    plan = []
    for table in tables:
        local_n, prod_n = _count(local, table), _count(prod, table)
        plan.append((table, local_n, prod_n))
        print(f"{table.name:<24} {local_n:>10,} {prod_n:>10,}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to replace local data with prod's.")
        return

    # One TRUNCATE for all selected tables so interdependent FKs do not
    # block each other; CASCADE covers dependents outside the selection.
    target_list = ", ".join(t.name for t in tables)
    logger.info("Truncating local: %s", target_list)
    with local.begin() as conn:
        conn.execute(text(f"TRUNCATE {target_list} RESTART IDENTITY CASCADE"))

    total = total_skipped = 0
    for table, _, prod_n in plan:
        logger.info("Copying %s (%d rows from prod)...", table.name, prod_n)
        copied, skipped = _copy_table(prod, local, table)
        total += copied
        total_skipped += skipped

    print(f"\nDone. {total:,} rows copied into local.")
    if total_skipped:
        print(
            f"WARNING: {total_skipped:,} rows could NOT be copied - they violate "
            f"constraints that local enforces and prod does not.\n"
            f"Local is not a byte-for-byte mirror. Fix the drift in prod."
        )
    print()
    print(f"{'table':<24} {'local':>10} {'prod':>10}")
    print("-" * 48)
    for table, _, prod_n in plan:
        print(f"{table.name:<24} {_count(local, table):>10,} {prod_n:>10,}")


if __name__ == "__main__":
    main()
