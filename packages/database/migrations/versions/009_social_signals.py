"""Create social signal intelligence tables.

Adds four tables for the Social Signal Intelligence feature:
- monitored_accounts: social accounts tracked for signal collection
- social_signals: individual posts collected from monitored accounts
- signal_clusters: aggregated clusters of related signals by theme
- weekly_pulses: weekly digests of social intelligence

Revision ID: 009
Revises: 008
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- monitored_accounts ---
    op.create_table(
        "monitored_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("handle", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=True),
        sa.Column("sector_tags", sa.JSON, nullable=True),
        sa.Column("authority_score", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("follower_count", sa.Integer, nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("profile_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
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
        sa.UniqueConstraint("platform", "handle", name="uq_platform_handle"),
    )
    op.create_index("ix_monitored_accounts_platform", "monitored_accounts", ["platform"])
    op.create_index("ix_monitored_accounts_account_type", "monitored_accounts", ["account_type"])

    # --- social_signals ---
    op.create_table(
        "social_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("post_url", sa.Text, nullable=False),
        sa.Column("author_handle", sa.String(255), nullable=True),
        sa.Column("author_display_name", sa.String(255), nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(32), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column("theme", sa.String(100), nullable=True),
        sa.Column("sub_theme", sa.String(100), nullable=True),
        sa.Column("entities", sa.JSON, nullable=True),
        sa.Column("sentiment", sa.Float, nullable=True),
        sa.Column("authority_score", sa.Float, nullable=True),
        sa.Column("signal_dimensions", sa.JSON, nullable=True),
        sa.Column("cluster_id", sa.String(36), nullable=True),
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
    op.create_index("ix_social_signals_platform", "social_signals", ["platform"])
    op.create_index("ix_social_signals_content_hash", "social_signals", ["content_hash"])
    op.create_index("ix_social_signals_published_at", "social_signals", ["published_at"])
    op.create_index("ix_social_signals_theme", "social_signals", ["theme"])
    op.create_index("ix_social_signals_cluster_id", "social_signals", ["cluster_id"])
    op.create_index(
        "ix_social_signals_platform_published",
        "social_signals",
        ["platform", "published_at"],
    )
    op.create_index(
        "ix_social_signals_theme_published",
        "social_signals",
        ["theme", "published_at"],
    )

    # --- signal_clusters ---
    op.create_table(
        "signal_clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("theme", sa.String(100), nullable=True),
        sa.Column("sub_theme", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("signal_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("composite_score", sa.Float, nullable=True),
        sa.Column("dimensions", sa.JSON, nullable=True),
        sa.Column("narrative_stage", sa.String(50), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("top_voices", sa.JSON, nullable=True),
        sa.Column("top_posts", sa.JSON, nullable=True),
        sa.Column("related_companies", sa.JSON, nullable=True),
        sa.Column("week_number", sa.Integer, nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
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
    op.create_index("ix_signal_clusters_slug", "signal_clusters", ["slug"])
    op.create_index("ix_signal_clusters_theme", "signal_clusters", ["theme"])
    op.create_index("ix_signal_clusters_composite_score", "signal_clusters", ["composite_score"])
    op.create_index(
        "ix_signal_clusters_year_week", "signal_clusters", ["year", "week_number"]
    )
    op.create_index(
        "ix_signal_clusters_theme_score", "signal_clusters", ["theme", "composite_score"]
    )

    # --- weekly_pulses ---
    op.create_table(
        "weekly_pulses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("accelerating_themes", sa.JSON, nullable=True),
        sa.Column("emerging_signals", sa.JSON, nullable=True),
        sa.Column("top_posts", sa.JSON, nullable=True),
        sa.Column("top_voices", sa.JSON, nullable=True),
        sa.Column("startups_to_watch", sa.JSON, nullable=True),
        sa.Column("sector_implications", sa.JSON, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agent_run_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
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
    op.create_index("ix_weekly_pulses_week_number", "weekly_pulses", ["week_number"])
    op.create_index("ix_weekly_pulses_slug", "weekly_pulses", ["slug"])
    op.create_index(
        "ix_weekly_pulses_year_week", "weekly_pulses", ["year", "week_number"]
    )


def downgrade() -> None:
    op.drop_index("ix_weekly_pulses_year_week", table_name="weekly_pulses")
    op.drop_index("ix_weekly_pulses_slug", table_name="weekly_pulses")
    op.drop_index("ix_weekly_pulses_week_number", table_name="weekly_pulses")
    op.drop_table("weekly_pulses")

    op.drop_index("ix_signal_clusters_theme_score", table_name="signal_clusters")
    op.drop_index("ix_signal_clusters_year_week", table_name="signal_clusters")
    op.drop_index("ix_signal_clusters_composite_score", table_name="signal_clusters")
    op.drop_index("ix_signal_clusters_theme", table_name="signal_clusters")
    op.drop_index("ix_signal_clusters_slug", table_name="signal_clusters")
    op.drop_table("signal_clusters")

    op.drop_index("ix_social_signals_theme_published", table_name="social_signals")
    op.drop_index("ix_social_signals_platform_published", table_name="social_signals")
    op.drop_index("ix_social_signals_cluster_id", table_name="social_signals")
    op.drop_index("ix_social_signals_theme", table_name="social_signals")
    op.drop_index("ix_social_signals_published_at", table_name="social_signals")
    op.drop_index("ix_social_signals_content_hash", table_name="social_signals")
    op.drop_index("ix_social_signals_platform", table_name="social_signals")
    op.drop_table("social_signals")

    op.drop_index("ix_monitored_accounts_account_type", table_name="monitored_accounts")
    op.drop_index("ix_monitored_accounts_platform", table_name="monitored_accounts")
    op.drop_table("monitored_accounts")
