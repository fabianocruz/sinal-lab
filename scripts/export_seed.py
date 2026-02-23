#!/usr/bin/env python3
"""Export published ContentPieces from the local DB to a JSON seed file.

Usage:
    python scripts/export_seed.py
    python scripts/export_seed.py --output scripts/seed_data.json
    python scripts/export_seed.py --agent-only
    python scripts/export_seed.py --output /tmp/export.json --agent-only --verbose

Requires DATABASE_URL environment variable or .env file.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import asc

from packages.database.config import SessionLocal
from packages.database.models.content_piece import ContentPiece

logger = logging.getLogger("export_seed")

# All known agent names for the summary breakdown.
KNOWN_AGENTS = ["sintese", "radar", "codigo", "funding", "mercado"]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Export published ContentPieces from DB to a JSON seed file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/seed_data.json",
        help="Output file path (default: scripts/seed_data.json)",
    )
    parser.add_argument(
        "--agent-only",
        action="store_true",
        help="Exclude pieces with no agent_name (non-agent content)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args()


def serialize_piece(piece: ContentPiece) -> Dict[str, Any]:
    """Serialize a ContentPiece ORM instance to an export dict.

    published_at is serialized as an ISO 8601 string with timezone offset.
    All Optional fields are included even when None so the schema is stable
    and consumers can rely on key presence.
    """
    published_at: Optional[str] = None
    if piece.published_at is not None:
        published_at = piece.published_at.isoformat()

    return {
        "slug": piece.slug,
        "title": piece.title,
        "subtitle": piece.subtitle,
        "body_md": piece.body_md,
        "summary": piece.summary,
        "content_type": piece.content_type,
        "agent_name": piece.agent_name,
        "agent_run_id": piece.agent_run_id,
        "confidence_dq": piece.confidence_dq,
        "confidence_ac": piece.confidence_ac,
        "sources": piece.sources or [],
        "metadata_": piece.metadata_ or {},
        "meta_description": piece.meta_description,
        "published_at": published_at,
        "review_status": piece.review_status,
        "author_name": piece.author_name,
    }


def query_pieces(agent_only: bool) -> List[ContentPiece]:
    """Query published ContentPieces from the database.

    Always filters by review_status='published'.
    When agent_only=True also requires agent_name IS NOT NULL.
    Results are ordered by published_at ASC for deterministic output.
    """
    session = SessionLocal()
    try:
        q = (
            session.query(ContentPiece)
            .filter(ContentPiece.review_status == "published")
            .order_by(asc(ContentPiece.published_at))
        )
        if agent_only:
            q = q.filter(ContentPiece.agent_name.isnot(None))
        pieces = q.all()
        # Detach from session before closing so attributes remain accessible.
        session.expunge_all()
        return pieces
    finally:
        session.close()


def build_summary(pieces: List[ContentPiece], output_path: str) -> str:
    """Build the human-readable summary line printed after export.

    Format: Exported N pieces (X sintese, Y radar, Z codigo, W funding, V mercado) to PATH
    Unknown agent names (or None) are counted but not broken out individually.
    """
    counts: Dict[str, int] = {name: 0 for name in KNOWN_AGENTS}
    for piece in pieces:
        if piece.agent_name in counts:
            counts[piece.agent_name] += 1

    breakdown = ", ".join(
        f"{counts[name]} {name}" for name in KNOWN_AGENTS
    )
    return f"Exported {len(pieces)} pieces ({breakdown}) to {output_path}"


def export(
    output_path: str,
    agent_only: bool = False,
    verbose: bool = False,
) -> List[ContentPiece]:
    """Fetch published pieces, serialize, and write to JSON file.

    Args:
        output_path: File path for the JSON output.
        agent_only: If True, exclude pieces with no agent_name.
        verbose: If True, log each piece being exported.

    Returns:
        The list of exported ContentPiece objects.

    Raises:
        OSError: If the output file cannot be written.
    """
    pieces = query_pieces(agent_only=agent_only)

    serialized = [serialize_piece(p) for p in pieces]

    if verbose:
        for item in serialized:
            logger.debug(
                "  %s  %s  %s",
                (item["agent_name"] or "\u2014").ljust(10),
                item["content_type"].ljust(12),
                item["slug"],
            )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as fh:
        json.dump(serialized, fh, ensure_ascii=False, indent=2)
        fh.write("\n")  # trailing newline for POSIX compliance

    return pieces


def main() -> None:
    """Entry point: parse CLI args, export, and print summary."""
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.debug("Output path: %s", args.output)
    logger.debug("Agent-only filter: %s", args.agent_only)

    try:
        pieces = export(args.output, agent_only=args.agent_only, verbose=args.verbose)
    except Exception as exc:
        print(f"ERROR: could not export \u2014 {exc}", file=sys.stderr)
        sys.exit(1)

    if not pieces:
        filter_note = " (agent-only)" if args.agent_only else ""
        print(f"No published pieces found{filter_note}. Nothing to export.")
        return

    print(build_summary(pieces, args.output))


if __name__ == "__main__":
    main()
