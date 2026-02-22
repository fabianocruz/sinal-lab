"""Add author_name column to content_pieces.

Revision ID: 004
Revises: 003
Create Date: 2026-02-21

Allows manually-created articles to display the real author name
instead of the "Sinal Editorial" placeholder.
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_pieces",
        sa.Column("author_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_pieces", "author_name")
