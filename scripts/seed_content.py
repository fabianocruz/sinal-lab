#!/usr/bin/env python3
"""Seed the content_pieces table from a JSON seed file.

Reads serialized ContentPiece dicts from a JSON file (produced by
scripts/export_seed.py) and inserts them into the database. Idempotent
by default — existing slugs are skipped. Use --force to re-insert.

Usage:
    python scripts/seed_content.py                     # insert into DB
    python scripts/seed_content.py --dry-run           # preview without writing
    python scripts/seed_content.py --force             # re-insert (delete existing by slug)
    python scripts/seed_content.py --file custom.json  # use a custom seed file

Requires DATABASE_URL environment variable or .env file.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)

DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "seed_data.json"

logger = logging.getLogger("seed_content")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for dry-run, force, and custom file."""
    parser = argparse.ArgumentParser(
        description="Seed content_pieces from a JSON seed file.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Re-insert existing slugs")
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help=f"Path to seed JSON file (default: {DEFAULT_SEED_FILE})",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return parser.parse_args()


def load_seed_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load seed data from a JSON file.

    The file must contain a JSON array of dicts, each with at least
    'slug', 'title', 'body_md', and 'content_type' keys.

    Returns:
        List of content piece dicts ready for insertion.

    Raises:
        FileNotFoundError: If the seed file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with file_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array, got {type(data).__name__}")

    return data


def _parse_published_at(value: Any) -> datetime:
    """Parse a published_at value into a timezone-aware datetime.

    Handles ISO 8601 strings (with or without timezone), bare dates
    (YYYY-MM-DD), and None (falls back to now).
    """
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    s = str(value).strip()

    # Try bare date first (e.g. 2025-09-01) — set default hour=6 UTC
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s, "%Y-%m-%d").replace(hour=6, tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    # Try ISO 8601 with timezone (e.g. 2025-09-01T12:00:00+00:00)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    logger.warning("Could not parse published_at '%s', using now()", value)
    return datetime.now(timezone.utc)


def seed(session: Any, pieces: List[Dict[str, Any]], *, force: bool = False) -> int:
    """Insert content pieces into content_pieces, skipping existing slugs.

    For each piece:
    1. Check if slug already exists in the database
    2. If --force, delete existing row before re-inserting
    3. Otherwise skip duplicates to make the script idempotent
    4. Insert with all available fields from the seed data
    """
    inserted = 0
    skipped = 0

    for item in pieces:
        slug = item["slug"]

        existing = session.execute(
            text("SELECT id FROM content_pieces WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()

        if existing:
            if force:
                session.execute(
                    text("DELETE FROM content_pieces WHERE slug = :slug"),
                    {"slug": slug},
                )
                logger.debug("Deleted existing: %s", slug)
            else:
                logger.debug("Skip (exists): %s", slug)
                skipped += 1
                continue

        published_at = _parse_published_at(item.get("published_at"))

        # Build insert params — use all fields from export_seed.py schema.
        params = {
            "id": str(uuid.uuid4()),
            "title": item["title"],
            "slug": slug,
            "subtitle": item.get("subtitle"),
            "body_md": item.get("body_md", ""),
            "summary": item.get("summary") or item.get("subtitle"),
            "content_type": item.get("content_type", "DATA_REPORT"),
            "agent_name": item.get("agent_name"),
            "agent_run_id": item.get("agent_run_id"),
            "confidence_dq": item.get("confidence_dq"),
            "confidence_ac": item.get("confidence_ac"),
            "review_status": item.get("review_status", "published"),
            "published_at": published_at,
            "meta_description": item.get("meta_description"),
            "author_name": item.get("author_name"),
        }

        # sources and metadata_ are JSONB — pass as JSON strings for raw SQL.
        sources = item.get("sources")
        metadata_ = item.get("metadata_")

        params["sources"] = json.dumps(sources) if sources else None
        params["metadata"] = json.dumps(metadata_) if metadata_ else None

        session.execute(
            text("""
                INSERT INTO content_pieces (
                    id, title, slug, subtitle, body_md, summary,
                    content_type, agent_name, agent_run_id,
                    confidence_dq, confidence_ac,
                    review_status, published_at, meta_description,
                    author_name, sources, metadata
                ) VALUES (
                    :id, :title, :slug, :subtitle, :body_md, :summary,
                    :content_type, :agent_name, :agent_run_id,
                    :confidence_dq, :confidence_ac,
                    :review_status, :published_at, :meta_description,
                    :author_name, CAST(:sources AS jsonb), CAST(:metadata AS jsonb)
                )
            """),
            params,
        )
        title_preview = item["title"][:60]
        print(f"  INSERT: {title_preview}... ({slug})")
        inserted += 1

    session.commit()
    print(f"\nDone: {inserted} inserted, {skipped} skipped.")
    return inserted


def main() -> None:
    """Entry point: load seed file, connect to DB, and seed content."""
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    seed_file = Path(args.file) if args.file else DEFAULT_SEED_FILE

    if not seed_file.exists():
        print(f"ERROR: seed file not found: {seed_file}", file=sys.stderr)
        print(
            "Generate it first with: python scripts/export_seed.py --output scripts/seed_data.json",
            file=sys.stderr,
        )
        sys.exit(1)

    pieces = load_seed_data(seed_file)
    print(f"Loaded {len(pieces)} pieces from {seed_file.name}")

    if args.dry_run:
        print("\n--- DRY RUN (no database writes) ---\n")
        for item in pieces:
            agent = (item.get("agent_name") or "-").ljust(10)
            ctype = (item.get("content_type") or "-").ljust(14)
            print(f"  {agent}  {ctype}  {item['slug']}")
        print(f"\nTotal: {len(pieces)} pieces")
        return

    db_display = DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"Connecting to: {db_display}")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        seed(session, pieces, force=args.force)


if __name__ == "__main__":
    main()
