#!/usr/bin/env python3
"""Seed the companies table from a CSV file.

Usage:
    python scripts/seed_companies.py                 # default CSV
    python scripts/seed_companies.py --csv path.csv  # custom CSV
    python scripts/seed_companies.py --dry-run       # preview without writing
"""

import argparse
import csv
import os
import sys
import uuid
from pathlib import Path

# Ensure the project root is on sys.path so we can import packages.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DEFAULT_CSV = Path(__file__).parent / "seed_companies.csv"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed companies table from CSV")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="Path to the CSV file (default: scripts/seed_companies.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows without writing to the database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop and re-insert all seeded companies (by slug)",
    )
    return parser.parse_args()


def load_csv(path: Path) -> list[dict]:
    """Read the CSV and return a list of row dicts."""
    if not path.exists():
        print(f"ERROR: CSV file not found: {path}")
        sys.exit(1)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} companies from {path}")
    return rows


def seed(session: Session, rows: list[dict], *, force: bool = False) -> int:
    """Insert companies into the database, skipping existing slugs."""
    inserted = 0
    skipped = 0

    for row in rows:
        slug = row["slug"]

        existing = session.execute(
            text("SELECT id FROM companies WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()

        if existing:
            if force:
                session.execute(
                    text("DELETE FROM companies WHERE slug = :slug"),
                    {"slug": slug},
                )
                print(f"  DELETED existing: {slug}")
            else:
                print(f"  SKIP (exists): {slug}")
                skipped += 1
                continue

        company_id = uuid.uuid4()
        session.execute(
            text("""
                INSERT INTO companies (
                    id, name, slug, short_description, sector, sub_sector,
                    city, state, country, business_model, website, status
                ) VALUES (
                    :id, :name, :slug, :short_description, :sector, :sub_sector,
                    :city, :state, :country, :business_model, :website, :status
                )
            """),
            {
                "id": company_id,
                "name": row["name"],
                "slug": slug,
                "short_description": row.get("short_description") or None,
                "sector": row.get("sector") or None,
                "sub_sector": row.get("sub_sector") or None,
                "city": row.get("city") or None,
                "state": row.get("state") or None,
                "country": row.get("country", "Brazil"),
                "business_model": row.get("business_model") or None,
                "website": row.get("website") or None,
                "status": row.get("status", "active"),
            },
        )
        print(f"  INSERT: {row['name']} ({slug})")
        inserted += 1

    session.commit()
    print(f"\nDone: {inserted} inserted, {skipped} skipped.")
    return inserted


def main() -> None:
    args = parse_args()
    rows = load_csv(args.csv)

    if args.dry_run:
        print("\n--- DRY RUN (no database writes) ---")
        for row in rows:
            print(f"  {row['name']:30s}  {row['slug']:25s}  {row.get('sector', '')}")
        print(f"\nTotal: {len(rows)} companies")
        return

    print(f"\nConnecting to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        seed(session, rows, force=args.force)


if __name__ == "__main__":
    main()
