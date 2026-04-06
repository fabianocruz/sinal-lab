"""Create watchlist_items table for user watchlists.

Stores per-user bookmarks of clusters and voices. Uses email as
the user identifier to keep auth simple.

Revision ID: 012
Revises: 011
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("item_slug", sa.String(255), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index("ix_watchlist_user_email", "watchlist_items", ["user_email"])
    op.create_index("ix_watchlist_user_type", "watchlist_items", ["user_email", "item_type"])

    # Unique constraint: one bookmark per user + type + slug
    op.create_unique_constraint(
        "uq_watchlist_user_type_slug",
        "watchlist_items",
        ["user_email", "item_type", "item_slug"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_watchlist_user_type_slug", "watchlist_items", type_="unique")
    op.drop_table("watchlist_items")
