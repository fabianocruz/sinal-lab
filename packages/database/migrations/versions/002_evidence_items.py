"""Evidence items table for unified cross-agent data.

Revision ID: 002
Revises: 001
Create Date: 2026-02-17

Stores normalized EvidenceItem records produced by all agents.
Used for cross-agent deduplication, editorial review, and publishing.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("territory", sa.String(100), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column("raw_data", sa.JSON, nullable=True),
        sa.Column("collector_run_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_items_content_hash", "evidence_items", ["content_hash"], unique=True)
    op.create_index("ix_evidence_items_agent_name", "evidence_items", ["agent_name"])
    op.create_index("ix_evidence_items_evidence_type", "evidence_items", ["evidence_type"])
    op.create_index("ix_evidence_items_territory", "evidence_items", ["territory"])
    op.create_index("ix_evidence_items_published_at", "evidence_items", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_evidence_items_published_at")
    op.drop_index("ix_evidence_items_territory")
    op.drop_index("ix_evidence_items_evidence_type")
    op.drop_index("ix_evidence_items_agent_name")
    op.drop_index("ix_evidence_items_content_hash")
    op.drop_table("evidence_items")
