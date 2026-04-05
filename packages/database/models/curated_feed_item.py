"""CuratedFeedItem model — editorially curated signals for the public feed."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class CuratedFeedItem(UUIDMixin, TimestampMixin, Base):
    """A curated social signal with editorial headline and context.

    Each item references a SocialSignal via content_hash (FK).
    Produced by the Feed Curator agent (persona: Ana Torres).
    """

    __tablename__ = "curated_feed_items"

    # FK to social_signals.content_hash
    content_hash: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True,
    )

    # Editorial content (produced by LLM)
    editorial_headline: Mapped[str] = mapped_column(String(120), nullable=False)
    editorial_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Source metadata (denormalized for fast reads)
    source_platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Media enrichment
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embed_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    embed_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    curated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )

    # Provenance
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_curated_feed_category_curated", "category", "curated_at"),
        Index("ix_curated_feed_relevance", "relevance_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<CuratedFeedItem(headline='{self.editorial_headline[:50]}', "
            f"category='{self.category}', score={self.relevance_score})>"
        )
