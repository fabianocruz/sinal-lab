"""EvidenceItemDB model — normalized evidence from all agents.

Maps to the evidence_items table created by migration 002.
Named EvidenceItemDB to avoid collision with the dataclass EvidenceItem
in apps.agents.base.evidence.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class EvidenceItemDB(UUIDMixin, TimestampMixin, Base):
    """A normalized evidence record produced by any agent.

    Used for cross-agent deduplication, editorial review, entity resolution,
    and publishing. Content is deduplicated by content_hash (MD5 of URL).
    """

    __tablename__ = "evidence_items"

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    # Optional metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Confidence and classification
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    territory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Flexible data
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Provenance
    collector_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<EvidenceItemDB(title='{self.title[:50]}', "
            f"type='{self.evidence_type}', agent='{self.agent_name}')>"
        )
