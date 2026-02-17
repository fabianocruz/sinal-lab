"""User model — platform users for waitlist and future dashboard."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """A platform user (waitlist subscriber or registered member).

    Starts as waitlist signup, transitions to founding member
    when onboarded. Stores newsletter preferences and role info.
    """

    __tablename__ = "users"

    # Identity
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Professional context
    role: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # founder, cto, engineer, investor, other
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Waitlist / membership
    waitlist_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_founding_member: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    onboarded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Newsletter preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="waitlist", index=True
    )  # waitlist, active, churned, banned

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_users_status_founding", "status", "is_founding_member"),
    )

    def __repr__(self) -> str:
        return (
            f"<User(email='{self.email}', role='{self.role}', "
            f"status='{self.status}')>"
        )
