#!/usr/bin/env python3
"""Import Resend audience contacts into the database.

Recovers subscribers that exist in Resend but were lost from the database
(e.g., after a DB reset). Preserves the original signup date from Resend.

Usage:
    # Preview what would be imported
    railway run python scripts/import_resend_contacts.py --dry-run

    # Execute the import
    railway run python scripts/import_resend_contacts.py --confirm

    # Local DB
    python scripts/import_resend_contacts.py --confirm
"""

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev",
)


def get_resend_contacts() -> list[dict]:
    """Fetch all contacts from the Resend audience."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    audience_id = os.environ.get("RESEND_AUDIENCE_ID", "")

    if not api_key or not audience_id:
        logger.error("RESEND_API_KEY or RESEND_AUDIENCE_ID not set")
        return []

    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://api.resend.com/audiences/{audience_id}/contacts"
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_existing_emails(session) -> set[str]:
    """Get all emails already in the database."""
    result = session.execute(text("SELECT lower(email) FROM users"))
    return {row[0] for row in result}


def import_contacts(
    contacts: list[dict],
    existing_emails: set[str],
    session,
    dry_run: bool = True,
) -> dict:
    """Import contacts that don't exist in the database.

    Uses the Resend created_at as the user's created_at to preserve
    the original signup date. All imported users get status='waitlist'.
    """
    imported = 0
    skipped = 0

    for contact in sorted(contacts, key=lambda c: c.get("created_at", "")):
        email = contact["email"].lower().strip()

        if email in existing_emails:
            skipped += 1
            continue

        first_name = contact.get("first_name", "")
        last_name = contact.get("last_name", "")
        name_parts = [p for p in [first_name, last_name] if p]
        name = " ".join(name_parts) if name_parts else None

        created_at = contact.get("created_at", "")

        if dry_run:
            logger.info(
                "  Would import: %s | name=%s | created=%s",
                email, name or "-", created_at[:19],
            )
        else:
            user_id = str(uuid.uuid4())
            session.execute(
                text("""
                    INSERT INTO users (id, email, name, status, created_at)
                    VALUES (:id, :email, :name, 'waitlist', :created_at)
                    ON CONFLICT (email) DO NOTHING
                """),
                {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "created_at": created_at,
                },
            )

        imported += 1
        existing_emails.add(email)

    return {"imported": imported, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Resend contacts to DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--confirm", action="store_true", help="Execute import")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("Usage: pass --dry-run to preview or --confirm to execute")
        sys.exit(2)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [import] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Fetching Resend contacts...")
    contacts = get_resend_contacts()
    logger.info("Found %d contacts in Resend", len(contacts))

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing = get_existing_emails(session)
        logger.info("Found %d existing users in DB", len(existing))

        to_import = [c for c in contacts if c["email"].lower().strip() not in existing]
        logger.info("Contacts to import: %d", len(to_import))

        if not to_import:
            logger.info("Nothing to import. DB is in sync with Resend.")
            return

        result = import_contacts(
            contacts, existing, session, dry_run=args.dry_run,
        )

        if args.dry_run:
            logger.info(
                "DRY RUN: would import %d, skip %d",
                result["imported"], result["skipped"],
            )
        else:
            session.commit()
            logger.info(
                "DONE: imported %d, skipped %d",
                result["imported"], result["skipped"],
            )
    except Exception:
        session.rollback()
        logger.error("Import failed, rolled back", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
