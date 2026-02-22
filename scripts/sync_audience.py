#!/usr/bin/env python3
"""Sync users to Resend Audience.

Reads users from PostgreSQL and adds them as contacts in the Resend
Audience (for newsletter broadcasts). By default syncs both active
and waitlist users. Use --status to filter by specific status.

Usage:
    python scripts/sync_audience.py
    python scripts/sync_audience.py --dry-run
    python scripts/sync_audience.py --status waitlist
    python scripts/sync_audience.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.config import get_settings
from apps.api.services.resend_audience import bulk_sync_contacts
from packages.database.models.user import User

logger = logging.getLogger(__name__)


def get_users(statuses: list[str] | None = None) -> list[dict]:
    """Fetch users from PostgreSQL, optionally filtered by status."""
    if statuses is None:
        statuses = ["active", "waitlist"]

    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).filter(User.status.in_(statuses)).all()
        contacts = []
        for user in users:
            contact = {"email": user.email}
            if user.name:
                # Use first word of name as first_name
                contact["first_name"] = user.name.split()[0]
            contacts.append(contact)
        return contacts
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync users to Resend Audience",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show contacts that would be synced without actually syncing",
    )
    parser.add_argument(
        "--status", type=str, default=None,
        help="Filter by user status (e.g. 'active', 'waitlist'). Default: both",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [sync-audience] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    statuses = [args.status] if args.status else None
    contacts = get_users(statuses)
    status_label = args.status or "active+waitlist"
    logger.info("Found %d %s users to sync", len(contacts), status_label)

    if not contacts:
        logger.info("No active users found. Nothing to sync.")
        return

    if args.dry_run:
        for c in contacts:
            logger.info("  Would sync: %s (%s)", c["email"], c.get("first_name", "—"))
        logger.info("Dry run — no contacts synced")
        return

    result = bulk_sync_contacts(contacts)

    if result["skipped"]:
        logger.warning("Sync skipped — RESEND_API_KEY or RESEND_AUDIENCE_ID not configured")
    else:
        logger.info(
            "Sync complete: %d synced, %d failed out of %d total",
            result["synced"],
            result["failed"],
            len(contacts),
        )


if __name__ == "__main__":
    main()
