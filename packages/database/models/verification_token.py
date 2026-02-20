"""VerificationToken model — email and magic-link verification tokens."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base


class VerificationToken(Base):
    """A one-time verification token for email verification or magic links.

    Tokens are consumed on use and have an expiration timestamp.
    The identifier is typically the user's email address.
    """

    __tablename__ = "verification_tokens"

    # No UUID primary key — use token as the unique identifier.
    # This matches NextAuth's adapter pattern.
    identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, primary_key=True
    )
    token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    expires: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<VerificationToken(identifier='{self.identifier}', "
            f"expires='{self.expires}')>"
        )
