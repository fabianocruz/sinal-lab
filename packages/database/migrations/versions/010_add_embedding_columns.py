"""Add embedding columns to social_signals and signal_clusters.

Adds:
- embedding_json (JSON): always populated, stores embedding as JSON array.
    Works on any PostgreSQL without extensions.
- embedding_vector (vector(1536)): populated only when pgvector is available.
    Enables fast cosine similarity search via <=> operator with IVFFlat index.

The migration checks for pgvector availability at runtime and gracefully
skips the vector column and index if the extension is not installed.

Revision ID: 010
Revises: 009
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _pgvector_available(connection) -> bool:
    """Check if pgvector extension can be created."""
    try:
        result = connection.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        )
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    connection = op.get_bind()

    # --- Always add embedding_json (plain JSON, universal) ---
    op.add_column(
        "social_signals",
        sa.Column("embedding_json", sa.JSON, nullable=True),
    )
    op.add_column(
        "signal_clusters",
        sa.Column("centroid_embedding_json", sa.JSON, nullable=True),
    )

    # --- Conditionally add pgvector columns ---
    has_pgvector = _pgvector_available(connection)

    if has_pgvector:
        # Enable extension
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Add vector columns using raw SQL (SQLAlchemy does not have a vector type)
        op.execute(
            "ALTER TABLE social_signals "
            "ADD COLUMN embedding_vector vector(1536)"
        )
        op.execute(
            "ALTER TABLE signal_clusters "
            "ADD COLUMN centroid_vector vector(1536)"
        )

        # IVFFlat index on social_signals for cosine similarity
        # lists=100 is good for up to ~100K rows
        op.execute(
            "CREATE INDEX ix_social_signals_embedding_vector "
            "ON social_signals "
            "USING ivfflat (embedding_vector vector_cosine_ops) "
            "WITH (lists = 100)"
        )

        # IVFFlat index on signal_clusters for cluster similarity
        op.execute(
            "CREATE INDEX ix_signal_clusters_centroid_vector "
            "ON signal_clusters "
            "USING ivfflat (centroid_vector vector_cosine_ops) "
            "WITH (lists = 20)"
        )
    else:
        # Log that pgvector is not available (no-op, columns skipped)
        # The application will use embedding_json with in-memory cosine similarity
        pass


def downgrade() -> None:
    connection = op.get_bind()

    # Check if vector columns exist before trying to drop
    try:
        result = connection.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'signal_clusters' "
                "AND column_name = 'centroid_vector'"
            )
        )
        if result.fetchone():
            op.drop_index("ix_signal_clusters_centroid_vector", table_name="signal_clusters")
            op.execute("ALTER TABLE signal_clusters DROP COLUMN centroid_vector")
    except Exception:
        pass

    try:
        result = connection.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'social_signals' "
                "AND column_name = 'embedding_vector'"
            )
        )
        if result.fetchone():
            op.drop_index("ix_social_signals_embedding_vector", table_name="social_signals")
            op.execute("ALTER TABLE social_signals DROP COLUMN embedding_vector")
    except Exception:
        pass

    op.drop_column("signal_clusters", "centroid_embedding_json")
    op.drop_column("social_signals", "embedding_json")
