"""Database persistence for the Feed Curator agent.

Persists CuratedItem instances to the curated_feed_items table.
Follows the same pattern as apps/agents/social_signals/db_writer.py:
the main entry point (persist_curated_feed) is passed as domain_persist_fn
to the orchestrator.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.agents.feed_curator.curator import CuratedItem

logger = logging.getLogger(__name__)


def _upsert_curated_item(
    session: Session,
    item: CuratedItem,
    agent_run_id: str = "",
) -> str:
    """Upsert a single CuratedFeedItem by content_hash.

    Uses content_hash as the dedup key (FK to social_signals).
    On conflict, updates editorial fields (headline, context, score)
    since the LLM may produce improved results on re-runs.

    Args:
        session: SQLAlchemy session (not committed).
        item: CuratedItem from curator.
        agent_run_id: Current agent run ID.

    Returns:
        "inserted" or "updated"
    """
    from packages.database.models.curated_feed_item import CuratedFeedItem

    existing = (
        session.query(CuratedFeedItem)
        .filter_by(content_hash=item.content_hash)
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing:
        existing.editorial_headline = item.editorial_headline
        existing.editorial_context = item.editorial_context
        existing.relevance_score = item.relevance_score
        existing.category = item.category
        existing.thumbnail_url = item.thumbnail_url or existing.thumbnail_url
        existing.embed_type = item.embed_type or existing.embed_type
        existing.embed_url = item.embed_url or existing.embed_url
        existing.agent_run_id = agent_run_id
        existing.updated_at = now
        return "updated"

    record = CuratedFeedItem(
        id=uuid4(),
        content_hash=item.content_hash,
        editorial_headline=item.editorial_headline,
        editorial_context=item.editorial_context,
        relevance_score=item.relevance_score,
        category=item.category,
        source_platform=item.source_platform,
        source_url=item.source_url,
        source_author=item.source_author,
        source_text=item.source_text[:500] if item.source_text else None,
        thumbnail_url=item.thumbnail_url,
        embed_type=item.embed_type,
        embed_url=item.embed_url,
        curated_at=now,
        agent_run_id=agent_run_id,
    )
    session.add(record)
    return "inserted"


def persist_curated_feed(
    agent: Any,
    agent_output: Any,
    session: Session,
) -> None:
    """Domain persistence callback for the orchestrator.

    Matches the signature expected by orchestrator's domain_persist_fn:
    (agent, agent_output, session) -> None.

    Args:
        agent: FeedCuratorAgent instance.
        agent_output: AgentOutput from agent.output().
        session: SQLAlchemy session (caller manages commit/rollback).
    """
    curated_items: List[CuratedItem] = getattr(agent, "_curated_items", [])
    run_id: str = getattr(agent, "run_id", "")

    stats: Dict[str, int] = {"inserted": 0, "updated": 0}

    for item in curated_items:
        result = _upsert_curated_item(session, item, agent_run_id=run_id)
        stats[result] = stats.get(result, 0) + 1

    session.flush()

    logger.info(
        "Feed Curator persistence complete: %d inserted, %d updated",
        stats["inserted"],
        stats["updated"],
    )
