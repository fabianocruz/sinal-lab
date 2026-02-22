"""Create company_external_ids table.

Revision ID: 005
Revises: 004
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_external_ids",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_slug", sa.String(255), nullable=False, index=True),
        sa.Column("id_type", sa.String(50), nullable=False),
        sa.Column("id_value", sa.String(500), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
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
        sa.UniqueConstraint("id_type", "id_value", name="uq_external_id_type_value"),
    )
    op.create_index(
        "ix_company_ext_ids_slug", "company_external_ids", ["company_slug"]
    )
    op.create_index(
        "ix_company_ext_ids_type_value",
        "company_external_ids",
        ["id_type", "id_value"],
    )


def downgrade() -> None:
    op.drop_index("ix_company_ext_ids_type_value", table_name="company_external_ids")
    op.drop_index("ix_company_ext_ids_slug", table_name="company_external_ids")
    op.drop_table("company_external_ids")
