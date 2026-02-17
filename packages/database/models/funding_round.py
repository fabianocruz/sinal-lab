"""FundingRound model — investment events in LATAM tech companies."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class FundingRound(UUIDMixin, TimestampMixin, Base):
    """A funding event for a company tracked by the platform.

    Links companies to investors via JSON references (company_slug,
    lead_investor_slugs, participant_slugs). Full FK relationships
    will be added when the ORM layer matures.
    """

    __tablename__ = "funding_rounds"

    # Company reference (slug-based for now, FK later)
    company_slug: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Round details
    round_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # pre-seed, seed, series_a, series_b, series_c, series_d, ipo, debt, grant
    amount_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amount_local: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    valuation_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Dates
    announced_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, index=True
    )
    closed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Investors (JSON arrays of slugs/names)
    lead_investors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    participants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Source and confidence
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_funding_company_round", "company_slug", "round_type"),
        Index("ix_funding_date_type", "announced_date", "round_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<FundingRound(company='{self.company_name}', "
            f"round='{self.round_type}', amount_usd={self.amount_usd})>"
        )
