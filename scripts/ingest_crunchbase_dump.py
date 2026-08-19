"""Parse + ingest manually-pasted Crunchbase LATAM funding rounds.

Input format (7 lines per entry, blank line between):
    CompanyName Logo
    CompanyName
    City, State, Country, Region
    Round Type
    $Amount or — (undisclosed)
    Date (e.g. "Apr 27, 2026")
    CompanyName raised $USDAmount on YYYY-MM-DD in Round Type

Usage:
    python3 scripts/ingest_crunchbase_dump.py data/crunchbase_latam_2026-04-21.txt --dry-run
    python3 scripts/ingest_crunchbase_dump.py data/crunchbase_latam_2026-04-21.txt
"""

import argparse
import logging
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from packages.database.models.funding_round import FundingRound  # noqa: E402
from packages.database.session import get_session  # noqa: E402

logger = logging.getLogger(__name__)

# Round types we ingest as real VC funding events.
# Excluded: Post-IPO Debt, Post-IPO Equity, Post-IPO Secondary, Secondary Market,
# Debt Financing, Grant, Non-equity Assistance, Private Equity (undisclosed),
# Corporate Round, Funding Round (generic).
VC_ROUND_TYPES = {
    "Seed": "seed",
    "Pre-Seed": "pre_seed",
    "Angel": "angel",
    "Series A": "series_a",
    "Series B": "series_b",
    "Series C": "series_c",
    "Series D": "series_d",
    "Series E": "series_e",
    "Series F": "series_f",
    "Venture - Series Unknown": "venture",
    "Initial Coin Offering": "ico",
}

# Date parsing: "Apr 27, 2026" format used by Crunchbase.
_DATE_RE = re.compile(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# "CompanyName raised $USDAmount on YYYY-MM-DD in Round Type"
_SUMMARY_RE = re.compile(
    r"raised\s+\$(\d+)\s+on\s+(\d{4}-\d{2}-\d{2})\s+in\s+(.+?)(?:\s+Round)?$"
)
# "CompanyName raised an undisclosed amount on YYYY-MM-DD in Round Type"
_UNDISCLOSED_RE = re.compile(
    r"raised\s+an\s+undisclosed\s+amount\s+on\s+(\d{4}-\d{2}-\d{2})\s+in\s+(.+?)(?:\s+Round)?$"
)


@dataclass
class ParsedRound:
    company_name: str
    company_slug: str
    city: Optional[str]
    country: Optional[str]
    round_type_raw: str
    round_type: str  # normalized
    amount_usd: Optional[float]
    announced_date: date
    source_url: str = "https://www.crunchbase.com"
    source_name: str = "crunchbase_manual_dump"


def _slugify(name: str) -> str:
    """Simple slugify: lowercase, alphanumeric+dash only."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-")


def _parse_date(date_str: str) -> Optional[date]:
    """Parse 'Apr 27, 2026' or '2026-04-27' format."""
    m = _DATE_RE.match(date_str)
    if m:
        month_name, day, year = m.groups()
        month = _MONTHS.get(month_name)
        if month:
            return date(int(year), month, int(day))
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_location(line: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (city, country) from 'City, State, Country, Region'."""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 3:
        return parts[0], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def parse_dump(text: str) -> list[ParsedRound]:
    """Parse the Crunchbase dump format into ParsedRound objects."""
    blocks = re.split(r"\n\s*\n", text.strip())
    rounds: list[ParsedRound] = []

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 6:
            continue

        # Line 0: "CompanyName Logo"
        # Line 1: CompanyName
        # Line 2: Location
        # Line 3: Round type
        # Line 4: Amount (or —)
        # Line 5: Date
        # Line 6: Summary "CompanyName raised ... in Round Type"

        name_line = lines[1]
        location_line = lines[2]
        round_type_raw = lines[3]
        # amount_line = lines[4]  # parsed from summary instead (USD normalized)
        date_line = lines[5]
        summary_line = lines[6] if len(lines) > 6 else ""

        if round_type_raw not in VC_ROUND_TYPES:
            continue  # skip non-VC rounds

        city, country = _parse_location(location_line)
        announced = _parse_date(date_line)
        if not announced:
            logger.warning("Skipping %s: bad date %r", name_line, date_line)
            continue

        amount_usd: Optional[float] = None
        m = _SUMMARY_RE.search(summary_line)
        if m:
            amount_str, _, _ = m.groups()
            try:
                amount_usd = float(amount_str)
            except ValueError:
                pass
        elif _UNDISCLOSED_RE.search(summary_line):
            amount_usd = None
        # else: amount stays None (unparseable summary)

        rounds.append(ParsedRound(
            company_name=name_line,
            company_slug=_slugify(name_line),
            city=city,
            country=country,
            round_type_raw=round_type_raw,
            round_type=VC_ROUND_TYPES[round_type_raw],
            amount_usd=amount_usd,
            announced_date=announced,
        ))

    return rounds


# Crunchbase profile cards update over time: the SAME deal can reappear in a
# later dump with a shifted announced_date (seen shifting by ~1 month). Dedup
# therefore matches on (slug, round_type) + compatible amount + date within
# this tolerance, never on the exact date.
DATE_TOLERANCE_DAYS = 30


def _same_deal(a: ParsedRound, b: ParsedRound) -> bool:
    """Whether two parsed rounds describe the same deal.

    Same company + round type, amounts compatible (equal, or one side
    undisclosed), and announced dates within DATE_TOLERANCE_DAYS.
    Different amounts within the window are treated as DIFFERENT deals
    (e.g. a seed extension) and both are kept.
    """
    if a.company_slug != b.company_slug or a.round_type != b.round_type:
        return False
    if (
        a.amount_usd is not None
        and b.amount_usd is not None
        and a.amount_usd != b.amount_usd
    ):
        return False
    return abs((a.announced_date - b.announced_date).days) <= DATE_TOLERANCE_DAYS


def dedup_rounds(rounds: list[ParsedRound]) -> list[ParsedRound]:
    """Remove intra-dump duplicates, keeping the oldest date as canonical."""
    unique: list[ParsedRound] = []
    dupes = 0
    for r in rounds:
        match = next((u for u in unique if _same_deal(u, r)), None)
        if match is None:
            unique.append(r)
            continue
        dupes += 1
        # Older date is canonical; keep the amount if either side has it.
        if r.announced_date < match.announced_date:
            match.announced_date = r.announced_date
        if match.amount_usd is None and r.amount_usd is not None:
            match.amount_usd = r.amount_usd
    if dupes:
        logger.info("Removed %d intra-dump duplicates", dupes)
    return unique


def upsert_round(session, r: ParsedRound) -> str:
    """Insert or merge a funding round, tolerating shifted announced dates.

    A DB row with the same (slug, round_type), compatible amount, and a
    date within DATE_TOLERANCE_DAYS is the same deal: keep the row,
    converge to the oldest announced_date, and fill a missing amount.
    """
    from datetime import timedelta

    window = timedelta(days=DATE_TOLERANCE_DAYS)
    candidates = (
        session.query(FundingRound)
        .filter_by(company_slug=r.company_slug, round_type=r.round_type)
        .filter(FundingRound.announced_date >= r.announced_date - window)
        .filter(FundingRound.announced_date <= r.announced_date + window)
        .order_by(FundingRound.announced_date)
        .all()
    )
    existing = next(
        (
            c
            for c in candidates
            if c.amount_usd is None
            or r.amount_usd is None
            or float(c.amount_usd) == r.amount_usd
        ),
        None,
    )
    if existing:
        updated = False
        # Older date is canonical (re-imports shift dates forward).
        if r.announced_date < existing.announced_date:
            existing.announced_date = r.announced_date
            updated = True
        if r.amount_usd and not existing.amount_usd:
            existing.amount_usd = r.amount_usd
            updated = True
        return "updated" if updated else "skipped"

    fr = FundingRound(
        id=uuid.uuid4(),
        company_name=r.company_name,
        company_slug=r.company_slug,
        round_type=r.round_type,
        amount_usd=r.amount_usd,
        currency="USD",
        announced_date=r.announced_date,
        source_url=r.source_url,
        source_name=r.source_name,
        confidence=0.8,  # Crunchbase is high-quality
        notes=f"Location: {r.city or '?'}, {r.country or '?'}. Original round type: {r.round_type_raw}.",
    )
    session.add(fr)
    return "inserted"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Crunchbase LATAM dump")
    parser.add_argument("path", help="Path to dump file")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    text = Path(args.path).read_text(encoding="utf-8")
    parsed = parse_dump(text)
    logger.info("Parsed %d VC funding rounds from dump", len(parsed))

    unique = dedup_rounds(parsed)
    logger.info("After dedup: %d unique rounds", len(unique))

    if args.dry_run:
        for r in sorted(unique, key=lambda x: x.announced_date, reverse=True):
            amt = f"${r.amount_usd:,.0f}" if r.amount_usd else "undisclosed"
            logger.info("  %s | %-14s | %-10s | %s | %s",
                        r.announced_date, r.round_type, amt, r.company_slug, r.country)
        logger.info("DRY RUN — %d rounds would be upserted", len(unique))
        return

    session = get_session()
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    try:
        for r in unique:
            action = upsert_round(session, r)
            stats[action] += 1
            if args.verbose:
                logger.debug("  %-10s %s %s %s", action.upper(), r.company_slug, r.round_type, r.announced_date)
        session.commit()
        logger.info("COMMITTED: %s", stats)
    except Exception as e:
        session.rollback()
        logger.error("Rolled back: %s", e, exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
