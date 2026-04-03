"""SignalCluster model — aggregated clusters of related social signals."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class SignalCluster(UUIDMixin, TimestampMixin, Base):
    """A cluster of related social signals sharing a common theme.

    Clusters are computed by the social intelligence agent and represent
    a coherent narrative or topic surfacing across monitored accounts.
    The composite_score combines all 8 signal dimensions into a single
    sortable relevance score.
    """

    __tablename__ = "signal_clusters"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Classification
    theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    sub_theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Signal volume
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Scoring
    composite_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # all 8 signal dimensions: volume, velocity, authority_concentration, etc.

    # Lifecycle
    narrative_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # emerging, accelerating, peaking, declining
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Representative content
    top_voices: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{handle, name, authority}]
    top_posts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{url, text, metrics}]
    related_companies: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # [{slug, name}]

    # Temporal bucketing
    week_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Provenance
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_signal_clusters_year_week", "year", "week_number"),
        Index("ix_signal_clusters_theme_score", "theme", "composite_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<SignalCluster(name='{self.name}', "
            f"theme='{self.theme}', stage='{self.narrative_stage}')>"
        )
