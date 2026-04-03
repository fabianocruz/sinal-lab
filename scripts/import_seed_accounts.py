#!/usr/bin/env python3
"""Import the seed list of monitored accounts from the curated Excel file.

Reads five sheets (Founders, VCs & Investidores, Executivos Bancos,
Thought Leaders, Empresas-Alvo) and upserts each row into the
monitored_accounts table.

Upsert logic: DELETE existing row by (platform, handle) then INSERT so
the record is always refreshed to the current seed data.

Usage:
    python scripts/import_seed_accounts.py                     # import into DB
    python scripts/import_seed_accounts.py --dry-run           # preview without writing
    python scripts/import_seed_accounts.py --verbose           # verbose logging
    python scripts/import_seed_accounts.py --file custom.xlsx  # custom Excel path

Requires DATABASE_URL environment variable or .env file at repo root.
"""

import argparse
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl is required. Install with: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

DEFAULT_EXCEL_FILE = (
    Path(__file__).resolve().parent.parent / "docs" / "Base_Curada_Signal_Intelligence.xlsx"
)

logger = logging.getLogger("import_seed_accounts")

# Authority scores by account type — thought leaders have the highest score
# because their primary value is opinion/insight, not institutional affiliation.
AUTHORITY_SCORES: Dict[str, float] = {
    "thought_leader": 0.8,
    "vc": 0.7,
    "company": 0.7,
    "founder": 0.6,
    "exec": 0.6,
}


@dataclass
class AccountRow:
    """Normalized representation of a single row from any sheet."""

    platform: str
    handle: str
    display_name: str
    account_type: str
    sector_tags: List[str]
    authority_score: float
    profile_url: Optional[str]
    metadata_: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# URL / handle extraction helpers
# ---------------------------------------------------------------------------

def _extract_linkedin_handle(url: Optional[str]) -> Optional[str]:
    """Extract a LinkedIn handle from a profile URL string.

    Handles common formats:
        linkedin.com/in/patrickcollison
        https://www.linkedin.com/in/patrickcollison/
        linkedin.com/company/stripe
        search needed  (→ None)

    Returns the slug after /in/ or /company/, lowercased, with trailing
    slash and query-string stripped.  Returns None when the URL is absent,
    empty, or a placeholder like "search needed".
    """
    if not url:
        return None

    url = url.strip()
    if not url or url.lower() in {"search needed", "n/a", "-", "tbd"}:
        return None

    # Normalise: strip scheme so matching is simpler.
    clean = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    clean = clean.rstrip("/").split("?")[0]

    # Match /in/<handle> or /company/<handle>
    match = re.search(r"linkedin\.com/(?:in|company)/([^/\s]+)", clean, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    logger.debug("Could not extract LinkedIn handle from: %r", url)
    return None


def _extract_twitter_handle(raw: Optional[str]) -> Optional[str]:
    """Extract a Twitter/X handle from a combined 'LinkedIn / X' cell.

    The cell may contain things like:
        linkedin.com/in/nikm
        linkedin.com/in/sytaylor  (no Twitter)
        @simon_taylor              (bare handle)
        x.com/simon_taylor
        twitter.com/simon_taylor
        linkedin.com/in/foo, @bar
    """
    if not raw:
        return None

    raw = raw.strip()

    # Look for explicit twitter.com or x.com URL
    match = re.search(r"(?:twitter|x)\.com/([A-Za-z0-9_]{1,50})", raw, re.IGNORECASE)
    if match:
        handle = match.group(1)
        if handle.lower() not in {"home", "search", "explore"}:
            return handle.lower()

    # Look for @handle token
    match = re.search(r"@([A-Za-z0-9_]{1,50})", raw)
    if match:
        return match.group(1).lower()

    return None


def _parse_tags(raw: Optional[str]) -> List[str]:
    """Split a comma/semicolon-separated tag string into a clean list."""
    if not raw:
        return []
    parts = re.split(r"[,;/]", str(raw))
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Per-sheet parsers
# ---------------------------------------------------------------------------

def _rows_from_sheet(ws: Any, skip_header: int = 1) -> List[Tuple]:
    """Return all non-empty data rows from a worksheet as value tuples."""
    rows = []
    for row in ws.iter_rows(min_row=skip_header + 1, values_only=True):
        # Skip completely empty rows
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        rows.append(row)
    return rows


def parse_founders(ws: Any) -> List[AccountRow]:
    """Parse Founders sheet.

    Columns: Nome, Empresa, Cargo, Região, Categoria, LinkedIn URL, Nota
    """
    accounts: List[AccountRow] = []
    for row in _rows_from_sheet(ws):
        name, company, role, region, category, linkedin_url, nota = (
            row + (None,) * 7
        )[:7]

        handle = _extract_linkedin_handle(str(linkedin_url) if linkedin_url else None)
        if not handle:
            logger.warning("Founders: no LinkedIn handle for %r — skipping", name)
            continue

        accounts.append(
            AccountRow(
                platform="linkedin",
                handle=handle,
                display_name=str(name) if name else handle,
                account_type="founder",
                sector_tags=_parse_tags(category),
                authority_score=AUTHORITY_SCORES["founder"],
                profile_url=str(linkedin_url).strip() if linkedin_url else None,
                metadata_={
                    "company": str(company) if company else None,
                    "role": str(role) if role else None,
                    "region": str(region) if region else None,
                    "nota": str(nota) if nota else None,
                    "source_sheet": "Founders",
                },
            )
        )
    return accounts


def parse_vcs(ws: Any) -> List[AccountRow]:
    """Parse VCs & Investidores sheet.

    Columns: Nome, Fundo/Firma, Cargo, Região, Foco, LinkedIn URL, Nota
    """
    accounts: List[AccountRow] = []
    for row in _rows_from_sheet(ws):
        name, firm, role, region, focus, linkedin_url, nota = (
            row + (None,) * 7
        )[:7]

        handle = _extract_linkedin_handle(str(linkedin_url) if linkedin_url else None)
        if not handle:
            logger.warning("VCs: no LinkedIn handle for %r — skipping", name)
            continue

        accounts.append(
            AccountRow(
                platform="linkedin",
                handle=handle,
                display_name=str(name) if name else handle,
                account_type="vc",
                sector_tags=_parse_tags(focus),
                authority_score=AUTHORITY_SCORES["vc"],
                profile_url=str(linkedin_url).strip() if linkedin_url else None,
                metadata_={
                    "firm": str(firm) if firm else None,
                    "role": str(role) if role else None,
                    "region": str(region) if region else None,
                    "nota": str(nota) if nota else None,
                    "source_sheet": "VCs & Investidores",
                },
            )
        )
    return accounts


def parse_executivos(ws: Any) -> List[AccountRow]:
    """Parse Executivos Bancos sheet.

    Columns: Nome, Organização, Cargo, Região, Categoria, LinkedIn URL, Nota
    """
    accounts: List[AccountRow] = []
    for row in _rows_from_sheet(ws):
        name, org, role, region, category, linkedin_url, nota = (
            row + (None,) * 7
        )[:7]

        handle = _extract_linkedin_handle(str(linkedin_url) if linkedin_url else None)
        if not handle:
            logger.warning("Executivos: no LinkedIn handle for %r — skipping", name)
            continue

        accounts.append(
            AccountRow(
                platform="linkedin",
                handle=handle,
                display_name=str(name) if name else handle,
                account_type="exec",
                sector_tags=_parse_tags(category),
                authority_score=AUTHORITY_SCORES["exec"],
                profile_url=str(linkedin_url).strip() if linkedin_url else None,
                metadata_={
                    "organization": str(org) if org else None,
                    "role": str(role) if role else None,
                    "region": str(region) if region else None,
                    "nota": str(nota) if nota else None,
                    "source_sheet": "Executivos Bancos",
                },
            )
        )
    return accounts


def parse_thought_leaders(ws: Any) -> List[AccountRow]:
    """Parse Thought Leaders sheet.

    Columns: Nome, Afiliação, Descrição, Região, Plataforma, Categoria,
             LinkedIn / X, Nota

    A row produces a LinkedIn entry when a handle is present, plus a
    separate Twitter entry when an X/Twitter handle is also present.
    """
    accounts: List[AccountRow] = []
    for row in _rows_from_sheet(ws):
        name, affiliation, description, region, platform_col, category, linkedin_x, nota = (
            row + (None,) * 8
        )[:8]

        raw_url = str(linkedin_x).strip() if linkedin_x else None

        linkedin_handle = _extract_linkedin_handle(raw_url)
        twitter_handle = _extract_twitter_handle(raw_url)

        base_metadata = {
            "affiliation": str(affiliation) if affiliation else None,
            "description": str(description) if description else None,
            "region": str(region) if region else None,
            "platforms_listed": str(platform_col) if platform_col else None,
            "nota": str(nota) if nota else None,
            "source_sheet": "Thought Leaders",
        }

        if linkedin_handle:
            accounts.append(
                AccountRow(
                    platform="linkedin",
                    handle=linkedin_handle,
                    display_name=str(name) if name else linkedin_handle,
                    account_type="thought_leader",
                    sector_tags=_parse_tags(category),
                    authority_score=AUTHORITY_SCORES["thought_leader"],
                    profile_url=f"linkedin.com/in/{linkedin_handle}",
                    metadata_=base_metadata,
                )
            )
        else:
            logger.warning("Thought Leaders: no LinkedIn handle for %r", name)

        if twitter_handle:
            accounts.append(
                AccountRow(
                    platform="twitter",
                    handle=twitter_handle,
                    display_name=str(name) if name else twitter_handle,
                    account_type="thought_leader",
                    sector_tags=_parse_tags(category),
                    authority_score=AUTHORITY_SCORES["thought_leader"],
                    profile_url=f"x.com/{twitter_handle}",
                    metadata_=base_metadata,
                )
            )

    return accounts


def parse_empresas(ws: Any) -> List[AccountRow]:
    """Parse Empresas-Alvo sheet.

    Columns: Empresa, Categoria, Estágio, Região, Investidores Notáveis,
             LinkedIn URL, Nota
    """
    accounts: List[AccountRow] = []
    for row in _rows_from_sheet(ws):
        empresa, category, stage, region, investors, linkedin_url, nota = (
            row + (None,) * 7
        )[:7]

        handle = _extract_linkedin_handle(str(linkedin_url) if linkedin_url else None)
        if not handle:
            logger.warning("Empresas: no LinkedIn handle for %r — skipping", empresa)
            continue

        accounts.append(
            AccountRow(
                platform="linkedin",
                handle=handle,
                display_name=str(empresa) if empresa else handle,
                account_type="company",
                sector_tags=_parse_tags(category),
                authority_score=AUTHORITY_SCORES["company"],
                profile_url=str(linkedin_url).strip() if linkedin_url else None,
                metadata_={
                    "stage": str(stage) if stage else None,
                    "region": str(region) if region else None,
                    "notable_investors": str(investors) if investors else None,
                    "nota": str(nota) if nota else None,
                    "source_sheet": "Empresas-Alvo",
                },
            )
        )
    return accounts


# ---------------------------------------------------------------------------
# Excel loader
# ---------------------------------------------------------------------------

# Maps sheet name substrings (lowercase) to their parser function.
SHEET_PARSERS = {
    "founders": parse_founders,
    "vcs": parse_vcs,
    "executivos": parse_executivos,
    "thought": parse_thought_leaders,
    "empresas": parse_empresas,
}


def load_accounts_from_excel(file_path: Path) -> List[AccountRow]:
    """Open the Excel workbook and parse all recognised sheets.

    Unknown sheets (Metodologia, Resumo, etc.) are silently skipped.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    all_accounts: List[AccountRow] = []

    for sheet_name in wb.sheetnames:
        key = sheet_name.lower()
        parser = None
        for prefix, fn in SHEET_PARSERS.items():
            if key.startswith(prefix):
                parser = fn
                break

        if parser is None:
            logger.debug("Skipping sheet: %s", sheet_name)
            continue

        ws = wb[sheet_name]
        parsed = parser(ws)
        logger.debug("Sheet '%s': parsed %d accounts", sheet_name, len(parsed))
        all_accounts.extend(parsed)

    return all_accounts


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

def upsert_accounts(conn: Any, accounts: List[AccountRow]) -> Dict[str, int]:
    """Upsert accounts into monitored_accounts.

    Strategy: DELETE by (platform, handle) then INSERT. This keeps the
    record fully refreshed on every seed run without requiring a complex
    ON CONFLICT DO UPDATE clause that varies by DB dialect.

    Returns a dict with counts: inserted, replaced, skipped_invalid.
    """
    counts: Dict[str, int] = {"inserted": 0, "replaced": 0, "skipped_invalid": 0}

    for acct in accounts:
        if not acct.handle or not acct.platform:
            logger.warning("Skipping invalid account (missing platform or handle): %r", acct)
            counts["skipped_invalid"] += 1
            continue

        # Check if already exists
        existing = conn.execute(
            text(
                "SELECT id FROM monitored_accounts "
                "WHERE platform = :platform AND handle = :handle"
            ),
            {"platform": acct.platform, "handle": acct.handle},
        ).fetchone()

        if existing:
            conn.execute(
                text(
                    "DELETE FROM monitored_accounts "
                    "WHERE platform = :platform AND handle = :handle"
                ),
                {"platform": acct.platform, "handle": acct.handle},
            )
            counts["replaced"] += 1
            logger.debug("Replaced: %s/%s", acct.platform, acct.handle)
        else:
            counts["inserted"] += 1
            logger.debug("Inserting: %s/%s", acct.platform, acct.handle)

        conn.execute(
            text("""
                INSERT INTO monitored_accounts (
                    id, platform, handle, display_name,
                    account_type, sector_tags, authority_score,
                    profile_url, is_active, metadata_,
                    created_at, updated_at
                ) VALUES (
                    :id, :platform, :handle, :display_name,
                    :account_type, CAST(:sector_tags AS json),
                    :authority_score, :profile_url, true,
                    CAST(:metadata_ AS json),
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
                "profile_url": acct.profile_url,
                "metadata_": json.dumps(acct.metadata_),
            },
        )

    return counts


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def _count_by_type(accounts: List[AccountRow]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for acct in accounts:
        counts[acct.account_type] = counts.get(acct.account_type, 0) + 1
    return counts


def _print_summary(accounts: List[AccountRow], db_counts: Optional[Dict[str, int]] = None) -> None:
    by_type = _count_by_type(accounts)

    type_labels = {
        "founder": "founders",
        "vc": "VCs",
        "exec": "executives",
        "thought_leader": "thought leaders",
        "company": "companies",
    }

    parts = []
    for key, label in type_labels.items():
        n = by_type.get(key, 0)
        if n:
            parts.append(f"{n} {label}")

    # Count entries without LinkedIn handle (skipped)
    total = sum(by_type.values())

    if db_counts:
        inserted = db_counts.get("inserted", 0)
        replaced = db_counts.get("replaced", 0)
        skipped = db_counts.get("skipped_invalid", 0)
        print(
            f"\nImported {inserted + replaced} accounts "
            f"({inserted} new, {replaced} refreshed"
            + (f", {skipped} skipped" if skipped else "")
            + f")"
        )
    else:
        print(f"\nTotal: {total} accounts")

    print(f"  Breakdown: {', '.join(parts)}")

    by_platform: Dict[str, int] = {}
    for acct in accounts:
        by_platform[acct.platform] = by_platform.get(acct.platform, 0) + 1
    platform_str = ", ".join(f"{p}: {n}" for p, n in sorted(by_platform.items()))
    print(f"  Platforms: {platform_str}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import monitored accounts from the curated Excel seed file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the Excel file and preview rows without writing to the database.",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help=f"Path to the Excel file (default: {DEFAULT_EXCEL_FILE})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    excel_path = Path(args.file) if args.file else DEFAULT_EXCEL_FILE

    print(f"Reading: {excel_path}")
    try:
        accounts = load_accounts_from_excel(excel_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(accounts)} account entries from Excel.")

    if args.dry_run:
        print("\n--- DRY RUN (no database writes) ---\n")
        col_w = 20
        print(f"  {'PLATFORM':<12} {'HANDLE':<{col_w}} {'TYPE':<14} DISPLAY NAME")
        print("  " + "-" * 70)
        for acct in accounts:
            handle_col = acct.handle[:col_w]
            print(
                f"  {acct.platform:<12} {handle_col:<{col_w}} "
                f"{acct.account_type:<14} {acct.display_name}"
            )
        _print_summary(accounts)
        return

    db_display = DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"Connecting to: {db_display}")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        db_counts = upsert_accounts(conn, accounts)

    _print_summary(accounts, db_counts=db_counts)


if __name__ == "__main__":
    main()
