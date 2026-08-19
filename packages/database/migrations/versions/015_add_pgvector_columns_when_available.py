"""Add pgvector columns when the extension is available.

Migration 010 added embedding_json unconditionally but only created the
vector(1536) columns when pgvector was available at the time it ran.
Production ran 010 before pgvector was enabled, so the columns were
skipped there. This migration retries: on a database where pgvector is
now available it enables the extension and adds any missing vector
columns + IVFFlat indexes; everywhere else it is a no-op.

Safe to run on databases where 010 already created everything — every
step checks for existence first.

Revision ID: 015
Revises: 014
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def _pgvector_available(connection) -> bool:
    try:
        result = connection.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        )
        return result.fetchone() is not None
    except Exception:
        return False


def _column_exists(connection, table: str, column: str) -> bool:
    result = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _index_exists(connection, name: str) -> bool:
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    connection = op.get_bind()

    if not _pgvector_available(connection):
        # SQLite or Postgres without pgvector: the app keeps using the
        # embedding_json fallback from migration 010.
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not _column_exists(connection, "social_signals", "embedding_vector"):
        op.execute(
            "ALTER TABLE social_signals ADD COLUMN embedding_vector vector(1536)"
        )
    if not _column_exists(connection, "signal_clusters", "centroid_vector"):
        op.execute(
            "ALTER TABLE signal_clusters ADD COLUMN centroid_vector vector(1536)"
        )

    # IVFFlat indexes for cosine similarity (lists sized for <100K rows,
    # same parameters as migration 010 used where it did run)
    if not _index_exists(connection, "ix_social_signals_embedding_vector"):
        op.execute(
            "CREATE INDEX ix_social_signals_embedding_vector "
            "ON social_signals "
            "USING ivfflat (embedding_vector vector_cosine_ops) "
            "WITH (lists = 100)"
        )
    if not _index_exists(connection, "ix_signal_clusters_centroid_vector"):
        op.execute(
            "CREATE INDEX ix_signal_clusters_centroid_vector "
            "ON signal_clusters "
            "USING ivfflat (centroid_vector vector_cosine_ops) "
            "WITH (lists = 20)"
        )


def downgrade() -> None:
    connection = op.get_bind()

    # Only drop what exists; leaves databases created by 010 untouched
    # in the same way 010's own downgrade would handle them.
    if _index_exists(connection, "ix_signal_clusters_centroid_vector"):
        op.execute("DROP INDEX ix_signal_clusters_centroid_vector")
    if _index_exists(connection, "ix_social_signals_embedding_vector"):
        op.execute("DROP INDEX ix_social_signals_embedding_vector")
    if _column_exists(connection, "signal_clusters", "centroid_vector"):
        op.execute("ALTER TABLE signal_clusters DROP COLUMN centroid_vector")
    if _column_exists(connection, "social_signals", "embedding_vector"):
        op.execute("ALTER TABLE social_signals DROP COLUMN embedding_vector")
