"""MonitoredAccount model — social accounts tracked for signal intelligence."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class MonitoredAccount(UUIDMixin, TimestampMixin, Base):
    """A social media account monitored for signal intelligence.

    Tracks founders, VCs, executives, and thought leaders across platforms.
    Authority score influences the weight given to their posts when computing
    signal dimensions.
    """

    __tablename__ = "monitored_accounts"

    # Platform identity
    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # twitter, linkedin, bluesky, reddit
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Classification
    account_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    # founder, vc, exec, thought_leader, company
    sector_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # e.g. ["fintech", "ai", "banking"]

    # Authority signals
    authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    follower_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Profile data
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("platform", "handle", name="uq_platform_handle"),
    )

    def __repr__(self) -> str:
        return (
            f"<MonitoredAccount(platform='{self.platform}', "
            f"handle='{self.handle}', type='{self.account_type}')>"
        )
