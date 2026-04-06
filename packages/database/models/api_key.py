"""ApiKey model — stores hashed API keys for public API authentication."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class ApiKey(UUIDMixin, TimestampMixin, Base):
    """An API key issued to a developer for programmatic access.

    The actual key is never stored. We store a SHA-256 hash and a short
    prefix (first 8 chars) for display purposes. The plaintext key is
    returned exactly once at creation time.
    """

    __tablename__ = "api_keys"

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ApiKey(email='{self.user_email}', "
            f"prefix='{self.key_prefix}', name='{self.name}')>"
        )
