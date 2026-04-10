"""Feedback model — NPS scores and comments from users.

Stores newsletter and platform feedback for the AutoPMF loop.
Each entry is tied to a content piece (edition) and optionally to a user.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class Feedback(UUIDMixin, TimestampMixin, Base):
    """A single feedback entry from a user.

    NPS scale: 0-10 (0 = would not recommend, 10 = would strongly recommend).
    Source: newsletter, dashboard, feed, api.
    """

    __tablename__ = "feedback"

    # Score
    nps_score: Mapped[int] = mapped_column(nullable=False)  # 0-10

    # Optional comment
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="newsletter"
    )  # newsletter, dashboard, feed
    content_slug: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, index=True
    )  # e.g. sinal-semanal-53
    edition: Mapped[Optional[int]] = mapped_column(nullable=True)

    # User (optional, anonymous feedback allowed)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # AutoPMF processing
    processed: Mapped[bool] = mapped_column(default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_feedback_source_edition", "source", "edition"),
        Index("ix_feedback_processed", "processed"),
    )

    def __repr__(self) -> str:
        return (
            f"<Feedback(nps={self.nps_score}, source='{self.source}', "
            f"edition={self.edition})>"
        )
