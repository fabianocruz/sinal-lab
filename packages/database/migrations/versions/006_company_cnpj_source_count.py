"""Add cnpj and source_count columns to companies.

Revision ID: 006
Revises: 005
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("cnpj", sa.String(14), nullable=True))
    op.add_column(
        "companies",
        sa.Column("source_count", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_companies_cnpj", "companies", ["cnpj"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_companies_cnpj", table_name="companies")
    op.drop_column("companies", "source_count")
    op.drop_column("companies", "cnpj")
