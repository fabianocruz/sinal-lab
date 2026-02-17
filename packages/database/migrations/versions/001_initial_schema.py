"""Initial schema — all 8 core tables.

Revision ID: 001
Revises:
Create Date: 2026-02-17

Tables: companies, content_pieces, agent_runs, data_provenance,
        investors, funding_rounds, ecosystems, users
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- companies ---
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("sub_sector", sa.String(100), nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default="Brazil"),
        sa.Column("founded_date", sa.Date, nullable=True),
        sa.Column("team_size", sa.Integer, nullable=True),
        sa.Column("tech_stack", sa.JSON, nullable=True),
        sa.Column("business_model", sa.String(50), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("twitter_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"])
    op.create_index("ix_companies_sector", "companies", ["sector"])
    op.create_index("ix_companies_city", "companies", ["city"])
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_companies_sector_city", "companies", ["sector", "city"])
    op.create_index("ix_companies_country_status", "companies", ["country", "status"])

    # --- content_pieces ---
    op.create_table(
        "content_pieces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False, unique=True),
        sa.Column("subtitle", sa.String(500), nullable=True),
        sa.Column("body_md", sa.Text, nullable=False),
        sa.Column("body_html", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=True),
        sa.Column("agent_run_id", sa.String(100), nullable=True),
        sa.Column("sources", sa.JSON, nullable=True),
        sa.Column("confidence_dq", sa.Float, nullable=True),
        sa.Column("confidence_ac", sa.Float, nullable=True),
        sa.Column("review_status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("reviewer", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_description", sa.String(320), nullable=True),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_pieces_slug", "content_pieces", ["slug"])
    op.create_index("ix_content_pieces_content_type", "content_pieces", ["content_type"])
    op.create_index("ix_content_pieces_agent_name", "content_pieces", ["agent_name"])
    op.create_index("ix_content_pieces_published_at", "content_pieces", ["published_at"])
    op.create_index("ix_content_type_status", "content_pieces", ["content_type", "review_status"])
    op.create_index("ix_content_agent_published", "content_pieces", ["agent_name", "published_at"])

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("run_id", sa.String(100), nullable=False, unique=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("items_collected", sa.Integer, nullable=True),
        sa.Column("items_processed", sa.Integer, nullable=True),
        sa.Column("items_output", sa.Integer, nullable=True),
        sa.Column("avg_confidence", sa.Float, nullable=True),
        sa.Column("confidence_distribution", sa.JSON, nullable=True),
        sa.Column("data_sources", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_content_id", sa.String(100), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    # --- data_provenance ---
    op.create_table(
        "data_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_type", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extraction_method", sa.String(50), nullable=False),
        sa.Column("collector_agent", sa.String(100), nullable=True),
        sa.Column("collector_run_id", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("quality_grade", sa.String(1), nullable=True),
        sa.Column("verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("raw_value", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_data_provenance_record_type", "data_provenance", ["record_type"])
    op.create_index("ix_data_provenance_record_id", "data_provenance", ["record_id"])
    op.create_index("ix_provenance_record", "data_provenance", ["record_type", "record_id"])
    op.create_index("ix_provenance_source", "data_provenance", ["source_name", "collected_at"])

    # --- investors ---
    op.create_table(
        "investors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("investor_type", sa.String(50), nullable=False, server_default="vc"),
        sa.Column("aum_usd", sa.Float, nullable=True),
        sa.Column("portfolio_count", sa.Integer, nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("thesis", sa.Text, nullable=True),
        sa.Column("focus_sectors", sa.JSON, nullable=True),
        sa.Column("focus_stages", sa.JSON, nullable=True),
        sa.Column("focus_regions", sa.JSON, nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("twitter_url", sa.String(500), nullable=True),
        sa.Column("crunchbase_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_investors_slug", "investors", ["slug"])
    op.create_index("ix_investors_investor_type", "investors", ["investor_type"])
    op.create_index("ix_investors_country", "investors", ["country"])
    op.create_index("ix_investors_status", "investors", ["status"])
    op.create_index("ix_investors_type_country", "investors", ["investor_type", "country"])

    # --- funding_rounds ---
    op.create_table(
        "funding_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_slug", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("round_type", sa.String(50), nullable=False),
        sa.Column("amount_usd", sa.Float, nullable=True),
        sa.Column("amount_local", sa.Float, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("valuation_usd", sa.Float, nullable=True),
        sa.Column("announced_date", sa.Date, nullable=True),
        sa.Column("closed_date", sa.Date, nullable=True),
        sa.Column("lead_investors", sa.JSON, nullable=True),
        sa.Column("participants", sa.JSON, nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_funding_rounds_company_slug", "funding_rounds", ["company_slug"])
    op.create_index("ix_funding_rounds_round_type", "funding_rounds", ["round_type"])
    op.create_index("ix_funding_rounds_announced_date", "funding_rounds", ["announced_date"])
    op.create_index("ix_funding_company_round", "funding_rounds", ["company_slug", "round_type"])
    op.create_index("ix_funding_date_type", "funding_rounds", ["announced_date", "round_type"])

    # --- ecosystems ---
    op.create_table(
        "ecosystems",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("total_startups", sa.Integer, nullable=True),
        sa.Column("total_funding_usd", sa.Float, nullable=True),
        sa.Column("active_investors", sa.Integer, nullable=True),
        sa.Column("total_exits", sa.Integer, nullable=True),
        sa.Column("top_sectors", sa.JSON, nullable=True),
        sa.Column("notable_companies", sa.JSON, nullable=True),
        sa.Column("ranking_score", sa.Float, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ecosystems_slug", "ecosystems", ["slug"])
    op.create_index("ix_ecosystems_country", "ecosystems", ["country"])
    op.create_index("ix_ecosystems_city", "ecosystems", ["city"])
    op.create_index("ix_ecosystems_country_city", "ecosystems", ["country", "city"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("waitlist_position", sa.Integer, nullable=True),
        sa.Column("is_founding_member", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", sa.JSON, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="waitlist"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_status_founding", "users", ["status", "is_founding_member"])


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("ecosystems")
    op.drop_table("funding_rounds")
    op.drop_table("investors")
    op.drop_table("data_provenance")
    op.drop_table("agent_runs")
    op.drop_table("content_pieces")
    op.drop_table("companies")
