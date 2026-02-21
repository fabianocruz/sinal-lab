"""Auth system — sessions, accounts, verification tokens, user auth fields.

Revision ID: 003
Revises: 002
Create Date: 2026-02-20

Extends the users table with authentication columns (password hash,
OAuth provider, email verification) and creates three new tables:
sessions, accounts (OAuth providers), and verification_tokens.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend users table with auth fields ---
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(50),
            nullable=False,
            server_default="email",
        ),
    )
    op.add_column(
        "users", sa.Column("auth_provider_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_token", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sessions_session_token", "sessions", ["session_token"], unique=True)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    # --- accounts (OAuth providers) ---
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("expires_at", sa.Integer, nullable=True),
        sa.Column("token_type", sa.String(50), nullable=True),
        sa.Column("scope", sa.String(255), nullable=True),
        sa.Column("id_token", sa.Text, nullable=True),
        sa.Column("session_state", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_accounts_provider_account"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_provider", "accounts", ["provider"])

    # --- verification_tokens ---
    op.create_table(
        "verification_tokens",
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_verification_tokens_token", "verification_tokens", ["token"], unique=True
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_index("ix_verification_tokens_token")
    op.drop_table("verification_tokens")

    op.drop_index("ix_accounts_provider")
    op.drop_index("ix_accounts_user_id")
    op.drop_table("accounts")

    op.drop_index("ix_sessions_user_id")
    op.drop_index("ix_sessions_session_token")
    op.drop_table("sessions")

    # Remove auth columns from users
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "auth_provider_id")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "password_hash")
