"""ContentPiece model — published content with confidence scoring."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class ContentPiece(UUIDMixin, TimestampMixin, Base):
    """A piece of content produced by an agent and reviewed for publication.

    Content types: DATA_REPORT, ANALYSIS, DEEP_DIVE, OPINION, INDEX, COMMUNITY, NEWS.
    Every piece carries confidence scores and review status per the editorial governance model.
    """

    __tablename__ = "content_pieces"

    # Identity
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # DATA_REPORT, ANALYSIS, DEEP_DIVE, OPINION, INDEX, COMMUNITY, NEWS

    # Provenance
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sources: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # Confidence scoring (editorial governance)
    confidence_dq: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Data Quality 1-5
    confidence_ac: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Analysis Confidence 1-5

    # Review
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft, pending_review, approved, published, retracted
    reviewer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Publication
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # SEO
    meta_description: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_content_type_status", "content_type", "review_status"),
        Index("ix_content_agent_published", "agent_name", "published_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContentPiece(title='{self.title[:50]}', "
            f"type='{self.content_type}', status='{self.review_status}')>"
        )
