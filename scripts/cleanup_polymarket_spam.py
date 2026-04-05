"""One-time cleanup: delete irrelevant Polymarket signals from database.

Removes Polymarket signals that are about sports, politics, entertainment,
etc. and do not match our core themes (AI, fintech, crypto, tech, startups).

Uses the same keyword list from the collector to ensure consistency.

Usage:
    DATABASE_URL=<url> python scripts/cleanup_polymarket_spam.py [--dry-run]
"""

import argparse
import sys
from contextlib import closing
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.database.session import get_session
from packages.database.models.social_signal import SocialSignal

# Same keywords used in the collector filter
from apps.agents.social_signals.collector import POLYMARKET_KEYWORDS


def _is_relevant(text: str) -> bool:
    """Check if a signal's text matches any of our topic keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in POLYMARKET_KEYWORDS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete irrelevant Polymarket signals from social_signals table"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview only, don't delete"
    )
    args = parser.parse_args()

    with closing(get_session()) as session:
        all_pm = (
            session.query(SocialSignal)
            .filter(SocialSignal.platform == "polymarket")
            .all()
        )

        irrelevant = [s for s in all_pm if not _is_relevant(s.text or "")]

        print(f"Total Polymarket signals: {len(all_pm)}")
        print(f"Irrelevant (to delete):   {len(irrelevant)}")
        print(f"Relevant (to keep):       {len(all_pm) - len(irrelevant)}")

        if irrelevant:
            print("\nSamples of signals to delete:")
            for s in irrelevant[:10]:
                preview = (s.text or "")[:80].replace("\n", " ")
                print(f"  - [{s.content_hash[:8]}] {preview}")

        if args.dry_run:
            print("\nDry run, no changes made.")
        else:
            if not irrelevant:
                print("\nNothing to delete.")
                return

            for s in irrelevant:
                session.delete(s)
            session.commit()
            print(f"\nDeleted {len(irrelevant)} irrelevant Polymarket signals.")


if __name__ == "__main__":
    main()
