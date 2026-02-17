"""Company model — startup profiles for the Sinal.lab platform."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class Company(UUIDMixin, TimestampMixin, Base):
    """A startup or tech company tracked by the platform.

    This is the core entity — agents produce intelligence about companies,
    and programmatic SEO pages are generated from company profiles.
    """

    __tablename__ = "companies"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Classification
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Brazil")

    # Company details
    founded_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    team_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    tech_stack: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    business_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Links
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )

    # Flexible metadata (for fields that don't warrant their own column yet)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_companies_sector_city", "sector", "city"),
        Index("ix_companies_country_status", "country", "status"),
    )

    def __repr__(self) -> str:
        return f"<Company(name='{self.name}', slug='{self.slug}', sector='{self.sector}')>"
