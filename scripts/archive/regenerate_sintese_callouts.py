"""One-off: regenerate editorial callouts for a published SINTESE edition.

Uses the current SINTESE writer prompts + existing items in the ContentPiece
metadata, so we can fix callouts without re-running the whole pipeline.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=False)

from apps.agents.sintese.collector import FeedItem  # noqa: E402
from apps.agents.sintese.scorer import ScoredItem  # noqa: E402
from apps.agents.sintese.synthesizer import NewsletterSection  # noqa: E402
from apps.agents.sintese.writer import SinteseWriter  # noqa: E402
from packages.database.models.content_piece import ContentPiece  # noqa: E402
from packages.database.session import get_session  # noqa: E402

logger = logging.getLogger(__name__)


def rebuild_sections_from_metadata(items_payload: list[dict]) -> list[NewsletterSection]:
    """Turn stored items dict back into NewsletterSections for the prompt."""
    section_labels = {}
    # Group items by section_heading if present; otherwise use a default section
    by_section: dict[str, list[ScoredItem]] = {}

    for item_data in items_payload:
        heading = item_data.get("section_heading") or "Destaques da Semana"
        feed_item = FeedItem(
            title=item_data.get("title", ""),
            url=item_data.get("url", ""),
            source_name=item_data.get("source_name", ""),
            summary=item_data.get("summary", ""),
        )
        scored = ScoredItem(
            item=feed_item,
            topic_score=item_data.get("composite_score", 0.5),
            recency_score=0.5,
            authority_score=0.5,
            latam_score=0.5,
        )
        by_section.setdefault(heading, []).append(scored)

    return [
        NewsletterSection(heading=h, items=items) for h, items in by_section.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate SINTESE callouts")
    parser.add_argument("slug", help="ContentPiece slug, e.g. sinal-semanal-55")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    session = get_session()
    try:
        piece = session.query(ContentPiece).filter_by(slug=args.slug).first()
        if not piece:
            logger.error("Slug not found: %s", args.slug)
            sys.exit(1)

        meta = piece.metadata_ or {}
        items = meta.get("items", [])
        edition_number = meta.get("edition_number") or 0
        if not items:
            logger.error("No items in metadata — cannot rebuild context")
            sys.exit(1)

        sections = rebuild_sections_from_metadata(items)
        logger.info(
            "Rebuilt %d sections with %d total items for edition #%d",
            len(sections),
            sum(len(s.items) for s in sections),
            edition_number,
        )

        writer = SinteseWriter()
        if not writer.is_available:
            logger.error("LLM client not available (ANTHROPIC_API_KEY?)")
            sys.exit(1)

        new_meta = writer.write_editorial_metadata(sections, edition_number)
        if not new_meta:
            logger.error("write_editorial_metadata returned None")
            sys.exit(1)

        logger.info("New callouts (%d):", len(new_meta.callouts))
        for i, c in enumerate(new_meta.callouts, 1):
            logger.info("  [%d] %s", i, c.get("content", "")[:200])

        if args.dry_run:
            logger.info("DRY RUN — not writing")
            return

        new_payload = dict(meta)
        new_payload["callouts"] = new_meta.callouts
        if new_meta.companies_mentioned:
            new_payload["companies_mentioned"] = new_meta.companies_mentioned
        if new_meta.topics:
            new_payload["topics"] = new_meta.topics
        piece.metadata_ = new_payload
        session.commit()
        logger.info("Updated %s with new callouts", args.slug)
    finally:
        session.close()


if __name__ == "__main__":
    main()
