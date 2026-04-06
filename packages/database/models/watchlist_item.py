"""WatchlistItem model — user-specific watchlist for clusters and voices."""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class WatchlistItem(UUIDMixin, TimestampMixin, Base):
    """A single item on a user's watchlist.

    Items can be clusters (by slug) or voices (by handle).
    Uses email as user identifier to avoid auth FK complexity.
    """

    __tablename__ = "watchlist_items"

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "cluster" or "voice"
    item_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_email", "item_type", "item_slug", name="uq_watchlist_user_type_slug"),
        Index("ix_watchlist_user_email", "user_email"),
        Index("ix_watchlist_user_type", "user_email", "item_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<WatchlistItem(email='{self.user_email}', "
            f"type='{self.item_type}', slug='{self.item_slug}')>"
        )
