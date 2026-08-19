"""Backfill real OpenAI embeddings for social_signals rows.

Production signals were persisted with zero-vector embeddings (neither
openai nor sklearn was installed, so the embeddings module degraded to
zeros — see apps/agents/social_signals/embeddings.py). This script
re-embeds every row whose embedding_json is missing or all zeros using
text-embedding-3-small, and mirrors the vector into the pgvector
column when it exists (migration 015).

Refuses to run without a working OpenAI key: backfill must never write
degraded vectors.

Usage:
    python3 scripts/backfill_signal_embeddings.py --dry-run
    python3 scripts/backfill_signal_embeddings.py
    DATABASE_URL=<prod-url> python3 scripts/backfill_signal_embeddings.py
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from sqlalchemy import text as sa_text  # noqa: E402

from apps.agents.social_signals.embeddings import (  # noqa: E402
    build_embedding_text,
    embed_texts,
)
from apps.agents.social_signals.similarity import (  # noqa: E402
    check_pgvector_available,
)
from packages.database.models.social_signal import SocialSignal  # noqa: E402

logger = logging.getLogger("backfill_embeddings")


def needs_backfill(embedding_json: Optional[List[float]]) -> bool:
    """A row needs backfill when it has no embedding or an inert one.

    Zero vectors are what the embeddings module produced without
    openai/sklearn installed — they carry no signal.
    """
    if not embedding_json:
        return True
    return not any(embedding_json)


def _vector_literal(vec: List[float]) -> str:
    """Format a vector as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(v)) for v in vec) + "]"


def backfill(session, batch_size: int = 100, dry_run: bool = False) -> dict:
    """Re-embed all signals with missing/zero embeddings.

    Returns:
        Stats dict: {"scanned", "backfilled", "skipped", "vector_column"}.
    """
    use_pgvector = check_pgvector_available(session)
    stats = {"scanned": 0, "backfilled": 0, "skipped": 0, "vector_column": use_pgvector}

    rows = (
        session.query(SocialSignal)
        .order_by(SocialSignal.created_at)
        .yield_per(batch_size)
    )

    batch: List[SocialSignal] = []
    for row in rows:
        stats["scanned"] += 1
        if not needs_backfill(row.embedding_json):
            stats["skipped"] += 1
            continue
        batch.append(row)
        if len(batch) >= batch_size:
            _process_batch(session, batch, use_pgvector, dry_run, stats)
            batch = []
    if batch:
        _process_batch(session, batch, use_pgvector, dry_run, stats)

    return stats


def _process_batch(session, batch, use_pgvector: bool, dry_run: bool, stats: dict) -> None:
    texts = [
        build_embedding_text(row.text or "", row.theme, row.sub_theme)
        for row in batch
    ]

    if dry_run:
        stats["backfilled"] += len(batch)
        logger.info("[dry-run] would embed %d signals", len(batch))
        return

    vectors = embed_texts(texts)
    if vectors is None:
        raise RuntimeError(
            "OpenAI embeddings unavailable (missing OPENAI_API_KEY or API "
            "failure). Aborting — backfill never writes degraded vectors."
        )

    for row, vec in zip(batch, vectors):
        row.embedding_json = vec
        if use_pgvector:
            session.execute(
                sa_text(
                    "UPDATE social_signals "
                    "SET embedding_vector = CAST(:vec AS vector) "
                    "WHERE id = :id"
                ),
                {"vec": _vector_literal(vec), "id": str(row.id)},
            )
    session.commit()
    stats["backfilled"] += len(batch)
    logger.info("Embedded %d signals (total: %d)", len(batch), stats["backfilled"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill OpenAI embeddings for social_signals"
    )
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from packages.database.session import get_session

    session = get_session()
    try:
        stats = backfill(session, batch_size=args.batch_size, dry_run=args.dry_run)
    finally:
        session.close()

    logger.info(
        "Done. scanned=%d backfilled=%d skipped=%d pgvector_column=%s%s",
        stats["scanned"],
        stats["backfilled"],
        stats["skipped"],
        stats["vector_column"],
        " (dry-run)" if args.dry_run else "",
    )


if __name__ == "__main__":
    main()
