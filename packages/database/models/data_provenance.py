"""DataProvenance model — tracks the origin of every data point."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class DataProvenance(UUIDMixin, TimestampMixin, Base):
    """Tracks the origin, method, and confidence of every data point ingested.

    This is the foundation of the platform's trust framework. Every piece of data
    — whether collected by an agent, submitted by a user, or scraped from a source —
    gets a provenance record linking it back to its origin.
    """

    __tablename__ = "data_provenance"

    # What record does this provenance belong to?
    record_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # company, funding_round, content_piece, etc.
    record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Where did the data come from?
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # When and how was it collected?
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # api, scraper, rss, manual, community

    # Who/what collected it?
    collector_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collector_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Quality
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    quality_grade: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )  # A, B, C, D

    # Verification
    verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # What specific field/data was this provenance for?
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_provenance_record", "record_type", "record_id"),
        Index("ix_provenance_source", "source_name", "collected_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<DataProvenance(record_type='{self.record_type}', "
            f"record_id='{self.record_id}', source='{self.source_name}')>"
        )
