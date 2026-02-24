"""Add funding_stage, total_funding_usd, is_trending to companies.

These fields support the redesigned Mapa de Startups UI which shows
funding stage badges, funding amounts, and trending indicators on
company cards.

Revision ID: 008
Revises: 007
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("funding_stage", sa.String(50), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("total_funding_usd", sa.Float, nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("is_trending", sa.Boolean, nullable=True, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("companies", "is_trending")
    op.drop_column("companies", "total_funding_usd")
    op.drop_column("companies", "funding_stage")
