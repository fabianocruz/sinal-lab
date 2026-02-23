"""Widen evidence_items.author and .url to TEXT.

- author: ArXiv papers frequently have many co-authors exceeding 255 chars.
- url: Google News RSS URLs use long base64-encoded redirect paths exceeding 2000 chars.

Using TEXT removes the limits for both columns.

Revision ID: 007
Revises: 006
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "evidence_items",
        "author",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "evidence_items",
        "url",
        existing_type=sa.String(2000),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "evidence_items",
        "url",
        existing_type=sa.Text(),
        type_=sa.String(2000),
        existing_nullable=False,
    )
    op.alter_column(
        "evidence_items",
        "author",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=True,
    )
