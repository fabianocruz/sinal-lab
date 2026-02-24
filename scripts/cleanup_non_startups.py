"""One-time cleanup: mark non-startup entries (universities, etc.) as inactive.

Scans all active companies in the database and deactivates any that match
non-startup name patterns (universities, government entities, etc.).

Usage:
    DATABASE_URL=<url> python scripts/cleanup_non_startups.py [--dry-run]
"""

import argparse
import sys
from contextlib import closing
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.database.session import get_session
from apps.agents.index.db_writer import cleanup_non_startups, _is_non_startup
from packages.database.models.company import Company


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup non-startup entries from companies table")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't modify database")
    args = parser.parse_args()

    with closing(get_session()) as session:
        if args.dry_run:
            companies = session.query(Company).filter(Company.status == "active").all()
            matches = [c for c in companies if _is_non_startup(c.name)]
            print(f"Found {len(matches)} non-startup entries (dry run, no changes):")
            for c in matches:
                print(f"  - {c.name} (slug={c.slug}, sector={c.sector})")
        else:
            count = cleanup_non_startups(session)
            session.commit()
            print(f"Deactivated {count} non-startup entries")


if __name__ == "__main__":
    main()
