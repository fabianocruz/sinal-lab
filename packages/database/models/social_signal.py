"""SocialSignal model — individual posts collected from monitored social accounts."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class SocialSignal(UUIDMixin, TimestampMixin, Base):
    """A single social media post collected during signal intelligence runs.

    Posts are deduplicated by content_hash (MD5 of the post URL).
    Signals are clustered by theme into SignalCluster records and
    aggregated into WeeklyPulse summaries.
    """

    __tablename__ = "social_signals"

    # Source
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    author_handle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    # Timing
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Engagement metrics
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # {likes, replies, reposts, quotes, views}

    # Classification
    theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entities: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{name, type}]

    # Scoring
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    authority_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    signal_dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # {volume, velocity, authority_concentration, ...}

    # Clustering
    cluster_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    # UUID as string — references signal_clusters.id

    # Provenance
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_social_signals_platform_published", "platform", "published_at"),
        Index("ix_social_signals_theme_published", "theme", "published_at"),
    )

    def __repr__(self) -> str:
        text_preview = (self.text or "")[:50]
        return (
            f"<SocialSignal(platform='{self.platform}', "
            f"author='{self.author_handle}', text='{text_preview}')>"
        )
