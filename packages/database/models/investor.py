"""Investor model — VC funds, angels, and accelerators tracked by the platform."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class Investor(UUIDMixin, TimestampMixin, Base):
    """A venture capital fund, angel investor, CVC, or accelerator.

    Investors are linked to funding rounds via the FundingRound model.
    Agent FUNDING tracks their activity in the LATAM ecosystem.
    """

    __tablename__ = "investors"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    investor_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="vc", index=True
    )  # vc, angel, cvc, accelerator, family_office, government

    # Financials
    aum_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    portfolio_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Strategy
    thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    focus_sectors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    focus_stages: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    focus_regions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Links
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    crunchbase_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_investors_type_country", "investor_type", "country"),
    )

    def __repr__(self) -> str:
        return (
            f"<Investor(name='{self.name}', slug='{self.slug}', "
            f"type='{self.investor_type}')>"
        )
