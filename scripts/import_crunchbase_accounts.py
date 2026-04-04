#!/usr/bin/env python3
"""Import monitored accounts from Crunchbase CSV exports.

Reads two CSV files:
  - investors CSV: Organization/Person Name, URL, Number of Investments, Number of Exits, Location
  - people CSV:    Full Name, URL, Primary Job Title, Primary Organization, URL, Location, CB Rank

Upsert logic: INSERT if (platform, handle) does not exist. Skip if it already
exists to avoid overwriting curated seed data from LinkedIn.

Usage:
    python scripts/import_crunchbase_accounts.py                        # import both
    python scripts/import_crunchbase_accounts.py --dry-run              # preview only
    python scripts/import_crunchbase_accounts.py --file-investors PATH  # custom investors CSV
    python scripts/import_crunchbase_accounts.py --file-people PATH     # custom people CSV
    python scripts/import_crunchbase_accounts.py --verbose              # debug logging

Requires DATABASE_URL in environment or .env at repo root.
"""

import argparse
import csv
import json
import logging
import math
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVESTORS_CSV = REPO_ROOT / "docs" / "investors-04-04-2026.csv"
DEFAULT_PEOPLE_CSV = REPO_ROOT / "docs" / "people-04-04-2026.csv"

logger = logging.getLogger("import_crunchbase_accounts")

# Keyword sets for account_type classification from job title.
# Checked in order — first match wins.
TITLE_TYPE_RULES: List[tuple] = [
    # (account_type, set of lowercase keywords to match against title)
    ("vc", {
        "partner", "general partner", "gp", "managing director",
        "managing partner", "investor", "venture", "principal",
        "investment associate", "investment manager",
    }),
    ("founder", {
        "founder", "co-founder", "cofounder", "co founder",
        "ceo", "chief executive",
    }),
    ("exec", {
        "cto", "cio", "coo", "cso", "cpo", "cmo", "cdo",
        "vp ", " vp", "vice president",
        "head of", "head,",
        "director", "chief ",
        "svp", "evp", "senior vice",
    }),
]


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class AccountRow:
    """Normalised representation of a single account to import."""

    platform: str
    handle: str
    display_name: str
    account_type: str
    sector_tags: List[str]
    authority_score: float
    profile_url: Optional[str]
    bio: Optional[str] = None
    location: Optional[str] = None
    metadata_: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# URL / slug helpers
# ---------------------------------------------------------------------------

def _extract_crunchbase_slug(url: Optional[str]) -> Optional[str]:
    """Extract the slug from a Crunchbase URL.

    Examples:
        https://www.crunchbase.com/organization/y-combinator  ->  y-combinator
        https://www.crunchbase.com/person/elad-gil            ->  elad-gil
        https://www.crunchbase.com/person/jeff-dean-2         ->  jeff-dean-2

    Returns None when the URL is absent or malformed.
    """
    if not url:
        return None
    url = url.strip()
    match = re.search(
        r"crunchbase\.com/(?:organization|person)/([^/?#\s]+)",
        url,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    logger.debug("Could not extract Crunchbase slug from: %r", url)
    return None


def _is_person_url(url: Optional[str]) -> bool:
    """Return True when the Crunchbase URL points to a person profile."""
    if not url:
        return False
    return "/person/" in url.lower()


# ---------------------------------------------------------------------------
# Authority score helpers
# ---------------------------------------------------------------------------

def _authority_from_investments(raw: Optional[str]) -> float:
    """Convert raw investment count to a normalised [0, 1] authority score.

    Uses a log scale so that the difference between 10 and 100 investments
    is meaningful, but the difference between 5000 and 8000 is not inflated.

    Scale reference (log10):
        1   investment  -> ~0.00
        10  investments -> ~0.18
        100 investments -> ~0.37
        500 investments -> ~0.50
        1000            -> ~0.55
        8157 (YC max)   -> ~0.68
    Capped at 1.0 (log10(max) / 6).
    """
    if not raw:
        return 0.3  # default for missing data

    # Strip commas from numbers like "8,157"
    clean = str(raw).replace(",", "").strip()
    try:
        count = int(clean)
    except ValueError:
        return 0.3

    if count <= 0:
        return 0.1

    # log10(count) normalised against log10(10_000) = 4, capped at 1.0
    score = math.log10(count + 1) / 4.0
    return round(min(score, 1.0), 4)


def _authority_from_cb_rank(raw: Optional[str]) -> float:
    """Convert CB Rank (Person) to authority score.

    Rank 1 = highest authority (1.0), Rank 1000 = lowest (0.0).
    Linear interpolation: score = 1 - ((rank - 1) / 999).
    """
    if not raw:
        return 0.5  # default for missing rank

    clean = str(raw).replace(",", "").strip()
    try:
        rank = int(clean)
    except ValueError:
        return 0.5

    rank = max(1, rank)
    score = 1.0 - (rank - 1) / 999.0
    return round(max(0.0, min(1.0, score)), 4)


# ---------------------------------------------------------------------------
# Account type classifier for job titles
# ---------------------------------------------------------------------------

def _classify_title(title: Optional[str]) -> str:
    """Classify a job title into an account_type string."""
    if not title:
        return "thought_leader"

    lower = title.lower()

    for account_type, keywords in TITLE_TYPE_RULES:
        for keyword in keywords:
            if keyword in lower:
                return account_type

    return "thought_leader"


# ---------------------------------------------------------------------------
# CSV parsers
# ---------------------------------------------------------------------------

def _clean_str(val: Optional[str]) -> Optional[str]:
    """Strip and return None for empty/whitespace strings."""
    if val is None:
        return None
    val = val.strip()
    return val if val else None


def parse_investors_csv(file_path: Path) -> List[AccountRow]:
    """Parse the investors CSV export from Crunchbase.

    Columns: Organization/Person Name, Organization/Person Name URL,
             Number of Investments, Number of Exits, Location

    Account type assignment:
    - URL contains /person/  -> angel (individual investor)
    - URL contains /organization/  -> vc (investment firm)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Investors CSV not found: {file_path}")

    accounts: List[AccountRow] = []
    skipped = 0

    with open(file_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = _clean_str(row.get("Organization/Person Name"))
            url = _clean_str(row.get("Organization/Person Name URL"))
            num_investments = _clean_str(row.get("Number of Investments"))
            num_exits = _clean_str(row.get("Number of Exits"))
            location = _clean_str(row.get("Location"))

            handle = _extract_crunchbase_slug(url)
            if not handle:
                logger.warning("Investors: no handle for %r — skipping", name)
                skipped += 1
                continue

            is_person = _is_person_url(url)
            account_type = "angel" if is_person else "vc"
            sector_tags = ["investor", "angel" if is_person else "vc"]

            authority = _authority_from_investments(num_investments)

            # Parse numeric fields, stripping commas
            def _to_int(val: Optional[str]) -> Optional[int]:
                if not val:
                    return None
                try:
                    return int(val.replace(",", ""))
                except ValueError:
                    return None

            investments_int = _to_int(num_investments)
            exits_int = _to_int(num_exits)

            accounts.append(
                AccountRow(
                    platform="crunchbase",
                    handle=handle,
                    display_name=name or handle,
                    account_type=account_type,
                    sector_tags=sector_tags,
                    authority_score=authority,
                    profile_url=url,
                    location=location,
                    metadata_={
                        "num_investments": investments_int,
                        "num_exits": exits_int,
                        "location": location,
                        "source_file": "investors-04-04-2026.csv",
                    },
                )
            )

    logger.debug(
        "Investors CSV: parsed %d accounts, skipped %d", len(accounts), skipped
    )
    return accounts


def parse_people_csv(file_path: Path) -> List[AccountRow]:
    """Parse the people CSV export from Crunchbase.

    Columns: Full Name, Full Name URL, Primary Job Title, Primary Organization,
             Primary Organization URL, Location, CB Rank (Person)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"People CSV not found: {file_path}")

    accounts: List[AccountRow] = []
    skipped = 0

    with open(file_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = _clean_str(row.get("Full Name"))
            url = _clean_str(row.get("Full Name URL"))
            title = _clean_str(row.get("Primary Job Title"))
            org = _clean_str(row.get("Primary Organization"))
            cb_rank = _clean_str(row.get("CB Rank (Person)"))
            location = _clean_str(row.get("Location"))

            handle = _extract_crunchbase_slug(url)
            if not handle:
                logger.warning("People: no handle for %r — skipping", name)
                skipped += 1
                continue

            account_type = _classify_title(title)
            authority = _authority_from_cb_rank(cb_rank)

            # Build bio from available fields
            if title and org:
                bio = f"{title} at {org}"
            elif title:
                bio = title
            elif org:
                bio = f"at {org}"
            else:
                bio = None

            # Parse CB Rank to int
            rank_int: Optional[int] = None
            if cb_rank:
                try:
                    rank_int = int(cb_rank.replace(",", ""))
                except ValueError:
                    pass

            accounts.append(
                AccountRow(
                    platform="crunchbase",
                    handle=handle,
                    display_name=name or handle,
                    account_type=account_type,
                    sector_tags=[account_type],
                    authority_score=authority,
                    profile_url=url,
                    bio=bio,
                    location=location,
                    metadata_={
                        "primary_job_title": title,
                        "primary_organization": org,
                        "cb_rank": rank_int,
                        "location": location,
                        "source_file": "people-04-04-2026.csv",
                    },
                )
            )

    logger.debug(
        "People CSV: parsed %d accounts, skipped %d", len(accounts), skipped
    )
    return accounts


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

def upsert_accounts(
    conn: Any, accounts: List[AccountRow]
) -> Dict[str, int]:
    """Insert accounts that do not yet exist by (platform, handle).

    Existing rows are left untouched to preserve curated seed data.
    Returns counts: inserted, skipped_existing, skipped_invalid.
    """
    counts: Dict[str, int] = {
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_invalid": 0,
    }

    for acct in accounts:
        if not acct.handle or not acct.platform:
            logger.warning(
                "Skipping invalid account (missing platform or handle): %r", acct
            )
            counts["skipped_invalid"] += 1
            continue

        existing = conn.execute(
            text(
                "SELECT id FROM monitored_accounts "
                "WHERE platform = :platform AND handle = :handle"
            ),
            {"platform": acct.platform, "handle": acct.handle},
        ).fetchone()

        if existing:
            logger.debug(
                "Skipping existing: %s/%s", acct.platform, acct.handle
            )
            counts["skipped_existing"] += 1
            continue

        conn.execute(
            text("""
                INSERT INTO monitored_accounts (
                    id, platform, handle, display_name,
                    account_type, sector_tags, authority_score,
                    bio, profile_url, is_active, metadata,
                    created_at, updated_at
                ) VALUES (
                    :id, :platform, :handle, :display_name,
                    :account_type, CAST(:sector_tags AS json),
                    :authority_score,
                    :bio, :profile_url, true,
                    CAST(:metadata AS json),
                    now(), now()
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "platform": acct.platform,
                "handle": acct.handle,
                "display_name": acct.display_name,
                "account_type": acct.account_type,
                "sector_tags": json.dumps(acct.sector_tags),
                "authority_score": acct.authority_score,
                "bio": acct.bio,
                "profile_url": acct.profile_url,
                "metadata": json.dumps(acct.metadata_),
            },
        )
        logger.debug("Inserted: %s/%s", acct.platform, acct.handle)
        counts["inserted"] += 1

    return counts


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def _count_by(accounts: List[AccountRow], attr: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for acct in accounts:
        key = str(getattr(acct, attr, "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _print_summary(
    investors: List[AccountRow],
    people: List[AccountRow],
    db_counts: Optional[Dict[str, int]] = None,
) -> None:
    all_accounts = investors + people
    total = len(all_accounts)

    print(f"\n{'='*60}")
    print("IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total parsed: {total}")
    print(f"  Investors CSV:  {len(investors)}")
    print(f"  People CSV:     {len(people)}")

    by_type = _count_by(all_accounts, "account_type")
    print("\nBy account type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:<20s} {n}")

    if db_counts:
        inserted = db_counts.get("inserted", 0)
        skipped_existing = db_counts.get("skipped_existing", 0)
        skipped_invalid = db_counts.get("skipped_invalid", 0)
        print(f"\nDatabase result:")
        print(f"  Inserted:         {inserted}")
        print(f"  Skipped (exists): {skipped_existing}")
        if skipped_invalid:
            print(f"  Skipped (invalid): {skipped_invalid}")
    else:
        print("\n[DRY RUN — no database writes]")

    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import monitored accounts from Crunchbase CSV exports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse CSVs and preview rows without writing to the database.",
    )
    parser.add_argument(
        "--file-investors",
        type=str,
        default=None,
        metavar="PATH",
        help=f"Path to investors CSV (default: {DEFAULT_INVESTORS_CSV.name})",
    )
    parser.add_argument(
        "--file-people",
        type=str,
        default=None,
        metavar="PATH",
        help=f"Path to people CSV (default: {DEFAULT_PEOPLE_CSV.name})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    return parser.parse_args()


def _dry_run_preview(accounts: List[AccountRow], label: str) -> None:
    print(f"\n--- {label} ({len(accounts)} rows) ---")
    col_w = 36
    print(f"  {'HANDLE':<{col_w}} {'TYPE':<16} {'SCORE':<7} DISPLAY NAME")
    print("  " + "-" * 90)
    for acct in accounts[:30]:
        handle_col = acct.handle[:col_w]
        print(
            f"  {handle_col:<{col_w}} {acct.account_type:<16} "
            f"{acct.authority_score:<7.4f} {acct.display_name}"
        )
    if len(accounts) > 30:
        print(f"  ... and {len(accounts) - 30} more rows (use --verbose to see all)")


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    investors_path = Path(args.file_investors) if args.file_investors else DEFAULT_INVESTORS_CSV
    people_path = Path(args.file_people) if args.file_people else DEFAULT_PEOPLE_CSV

    # Parse CSVs
    print(f"Reading investors: {investors_path}")
    try:
        investors = parse_investors_csv(investors_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  Parsed {len(investors)} investor accounts.")

    print(f"Reading people:    {people_path}")
    try:
        people = parse_people_csv(people_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  Parsed {len(people)} people accounts.")

    if args.dry_run:
        if args.verbose:
            _dry_run_preview(investors, "INVESTORS")
            _dry_run_preview(people, "PEOPLE")
        _print_summary(investors, people)
        return

    # Connect and upsert
    db_display = DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"\nConnecting to: {db_display}")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        print("Upserting investors...")
        inv_counts = upsert_accounts(conn, investors)
        print("Upserting people...")
        ppl_counts = upsert_accounts(conn, people)

    # Merge counts
    db_counts = {
        "inserted": inv_counts["inserted"] + ppl_counts["inserted"],
        "skipped_existing": inv_counts["skipped_existing"] + ppl_counts["skipped_existing"],
        "skipped_invalid": inv_counts["skipped_invalid"] + ppl_counts["skipped_invalid"],
    }

    _print_summary(investors, people, db_counts=db_counts)

    # Show post-import DB breakdown
    print("\nPost-import DB breakdown:")
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT account_type, platform, COUNT(*) as n "
                "FROM monitored_accounts "
                "GROUP BY account_type, platform "
                "ORDER BY COUNT(*) DESC"
            )
        )
        for r in result:
            print(f"  {str(r[0]):<20s} {str(r[1]):<15s} {r[2]}")


if __name__ == "__main__":
    main()
