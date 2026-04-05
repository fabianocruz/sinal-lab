"""Create curated_feed_items table for the Feed Curator agent.

Stores editorially curated social signals with LLM-generated headlines,
context, relevance scores, and media enrichment (thumbnails, embeds).

content_hash is a FK referencing social_signals.content_hash.

Revision ID: 011
Revises: 010
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curated_feed_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_hash", sa.String(32), nullable=False, unique=True),
        sa.Column("editorial_headline", sa.String(120), nullable=False),
        sa.Column("editorial_context", sa.Text, nullable=True),
        sa.Column("relevance_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("source_platform", sa.String(20), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_author", sa.String(255), nullable=True),
        sa.Column("source_text", sa.Text, nullable=True),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("embed_type", sa.String(20), nullable=True),
        sa.Column("embed_url", sa.Text, nullable=True),
        sa.Column("curated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agent_run_id", sa.String(100), nullable=True),
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

    # FK to social_signals.content_hash
    op.create_foreign_key(
        "fk_curated_feed_content_hash",
        "curated_feed_items",
        "social_signals",
        ["content_hash"],
        ["content_hash"],
    )

    # Indexes
    op.create_index("ix_curated_feed_content_hash", "curated_feed_items", ["content_hash"])
    op.create_index("ix_curated_feed_category", "curated_feed_items", ["category"])
    op.create_index("ix_curated_feed_curated_at", "curated_feed_items", ["curated_at"])
    op.create_index(
        "ix_curated_feed_category_curated",
        "curated_feed_items",
        ["category", "curated_at"],
    )
    op.create_index("ix_curated_feed_relevance", "curated_feed_items", ["relevance_score"])


def downgrade() -> None:
    op.drop_constraint("fk_curated_feed_content_hash", "curated_feed_items", type_="foreignkey")
    op.drop_table("curated_feed_items")
