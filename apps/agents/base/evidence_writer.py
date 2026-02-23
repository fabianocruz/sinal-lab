"""Evidence writer — persists EvidenceItem records to the database.

Handles upsert by content_hash with confidence-based merge logic:
higher confidence wins. Supports single items, batches, and raw
agent-specific items (via normalize_any).

Usage:
    from apps.agents.base.evidence_writer import persist_evidence_batch

    stats = persist_evidence_batch(session, evidence_items)
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from apps.agents.base.evidence import EvidenceItem
from apps.agents.base.normalizer import normalize_any
from packages.database.models.evidence_item import EvidenceItemDB

logger = logging.getLogger(__name__)

# Column size limits from EvidenceItemDB model.
# Used for defensive truncation to prevent DB errors.
_FIELD_LIMITS = {
    "title": 500,
    "source_name": 255,
    "evidence_type": 50,
    "agent_name": 100,
    "territory": 100,
    "collector_run_id": 100,
    # url, author, summary are Text (no limit) — not included here.
}


def _truncate_fields(item: EvidenceItem) -> EvidenceItem:
    """Truncate string fields to column limits, logging warnings.

    Modifies the item in place and returns it for chaining.
    """
    for field, limit in _FIELD_LIMITS.items():
        value = getattr(item, field, None)
        if value is not None and isinstance(value, str) and len(value) > limit:
            logger.warning(
                "Truncating evidence %s.%s from %d to %d chars (hash=%s)",
                type(item).__name__,
                field,
                len(value),
                limit,
                getattr(item, "content_hash", "?"),
            )
            setattr(item, field, value[:limit])
    return item


def persist_evidence_item(
    session: Session,
    item: EvidenceItem,
    collector_run_id: Optional[str] = None,
    confidence_wins: bool = True,
) -> str:
    """Upsert a single EvidenceItem by content_hash.

    If a record with the same content_hash exists:
    - If confidence_wins and new confidence > existing: update
    - Otherwise: skip

    Args:
        session: SQLAlchemy session.
        item: EvidenceItem to persist.
        collector_run_id: Optional run ID for provenance tracking.
        confidence_wins: If True, higher confidence overwrites (default True).

    Returns:
        Action taken: "inserted", "updated", or "skipped".
    """
    _truncate_fields(item)

    existing = (
        session.query(EvidenceItemDB)
        .filter_by(content_hash=item.content_hash)
        .first()
    )

    if existing:
        if confidence_wins and item.confidence > existing.confidence:
            existing.title = item.title
            existing.url = item.url
            existing.source_name = item.source_name
            existing.evidence_type = item.evidence_type.value if hasattr(item.evidence_type, "value") else item.evidence_type
            existing.agent_name = item.agent_name
            existing.confidence = item.confidence
            existing.summary = item.summary
            existing.author = item.author
            existing.tags = item.tags if item.tags else None
            existing.territory = item.territory
            existing.metrics = item.metrics if item.metrics else None
            existing.raw_data = item.raw_data if item.raw_data else None
            if item.published_at:
                existing.published_at = item.published_at
            if collector_run_id:
                existing.collector_run_id = collector_run_id
            logger.debug(
                "Updated evidence %s (confidence: %.2f -> %.2f)",
                item.content_hash,
                existing.confidence,
                item.confidence,
            )
            return "updated"
        else:
            logger.debug(
                "Skipped evidence %s (existing confidence %.2f >= new %.2f)",
                item.content_hash,
                existing.confidence,
                item.confidence,
            )
            return "skipped"

    evidence_type_val = item.evidence_type.value if hasattr(item.evidence_type, "value") else item.evidence_type

    db_item = EvidenceItemDB(
        id=uuid.uuid4(),
        title=item.title,
        url=item.url,
        source_name=item.source_name,
        evidence_type=evidence_type_val,
        agent_name=item.agent_name,
        content_hash=item.content_hash,
        published_at=item.published_at,
        summary=item.summary,
        author=item.author,
        tags=item.tags if item.tags else None,
        confidence=item.confidence,
        territory=item.territory,
        metrics=item.metrics if item.metrics else None,
        raw_data=item.raw_data if item.raw_data else None,
        collector_run_id=collector_run_id,
    )

    session.add(db_item)
    logger.debug("Inserted evidence %s", item.content_hash)
    return "inserted"


def persist_evidence_batch(
    session: Session,
    items: List[EvidenceItem],
    collector_run_id: Optional[str] = None,
) -> Dict[str, int]:
    """Batch upsert EvidenceItems.

    Args:
        session: SQLAlchemy session.
        items: List of EvidenceItem to persist.
        collector_run_id: Optional run ID for provenance tracking.

    Returns:
        Stats dict: {"inserted": X, "updated": Y, "skipped": Z}.
    """
    stats: Dict[str, int] = {"inserted": 0, "updated": 0, "skipped": 0}

    for item in items:
        action = persist_evidence_item(
            session, item, collector_run_id=collector_run_id
        )
        stats[action] += 1

    session.commit()

    logger.info(
        "Evidence batch: %d inserted, %d updated, %d skipped",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
    )
    return stats


def persist_raw_items(
    session: Session,
    raw_items: List[Any],
    agent_name: str,
    collector_run_id: Optional[str] = None,
) -> Dict[str, int]:
    """Normalize agent-specific items via normalize_any() then batch-persist.

    Args:
        session: SQLAlchemy session.
        raw_items: List of agent-specific data objects (FeedItem, TrendSignal, etc.).
        agent_name: Name of the producing agent.
        collector_run_id: Optional run ID for provenance tracking.

    Returns:
        Stats dict: {"inserted": X, "updated": Y, "skipped": Z}.

    Raises:
        ValueError: If any item type is not recognized by normalize_any().
    """
    if not raw_items:
        return {"inserted": 0, "updated": 0, "skipped": 0}

    evidence_items = [normalize_any(item, agent_name) for item in raw_items]
    return persist_evidence_batch(
        session, evidence_items, collector_run_id=collector_run_id
    )
