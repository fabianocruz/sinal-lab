"""Ecosystem model — city/region tech ecosystem profiles."""

from typing import Optional

from sqlalchemy import Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class Ecosystem(UUIDMixin, TimestampMixin, Base):
    """A city or region tech ecosystem profile.

    Tracks the health, size, and composition of local startup
    ecosystems across Latin America. Used for city-level
    programmatic SEO pages and comparative analysis.
    """

    __tablename__ = "ecosystems"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metrics
    total_startups: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_funding_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active_investors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_exits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Analysis
    top_sectors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notable_companies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    ranking_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_ecosystems_country_city", "country", "city"),
    )

    def __repr__(self) -> str:
        return (
            f"<Ecosystem(name='{self.name}', slug='{self.slug}', "
            f"country='{self.country}')>"
        )
