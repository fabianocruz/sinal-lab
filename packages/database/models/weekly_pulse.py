"""WeeklyPulse model — weekly social intelligence digest."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class WeeklyPulse(UUIDMixin, TimestampMixin, Base):
    """A weekly digest of social intelligence signals.

    Aggregates the top clusters, voices, and posts from a given week
    into a structured record used to generate editorial content and
    programmatic SEO pages.

    One WeeklyPulse per (year, week_number) pair — enforced via slug uniqueness
    (slug format: "pulse-{year}-w{week:02d}").
    """

    __tablename__ = "weekly_pulses"

    # Temporal identity
    week_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Signal highlights
    accelerating_themes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{name, score, delta}]
    emerging_signals: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{name, score, platforms}]
    top_posts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{url, text, author, metrics}]
    top_voices: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{handle, name, signal_count}]

    # Editorial intelligence
    startups_to_watch: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{slug, name, reason}]
    sector_implications: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{sector, implication}]

    # Generation metadata
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    # draft, published, archived

    __table_args__ = (
        Index("ix_weekly_pulses_year_week", "year", "week_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeeklyPulse(slug='{self.slug}', "
            f"year={self.year}, week={self.week_number}, status='{self.status}')>"
        )
