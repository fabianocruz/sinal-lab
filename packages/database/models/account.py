"""Account model — OAuth provider accounts linked to users."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base


class Account(Base):
    """An OAuth provider account linked to a user.

    Stores OAuth tokens and provider-specific data (Google, GitHub, etc.).
    A user can have multiple accounts from different providers.
    """

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # OAuth tokens
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    id_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_account_id", name="uq_accounts_provider_account"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Account(provider='{self.provider}', "
            f"user_id='{self.user_id}')>"
        )
