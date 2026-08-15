"""Record which signals a cluster is made of, for stable cluster identity.

The upsert key for signal_clusters was a slug of the name an LLM generated
for the cluster. That name is regenerated on every run, so a re-worded label
produced an INSERT instead of an UPDATE: production accumulated ~277 rows a
week for what is really ~10 clusters.

Membership could not be recovered from social_signals.cluster_id, which
records the cluster a signal landed in when it was first written, not the
composition of each cluster at each run. This column stores that composition
explicitly so the next run can recognise a bucket it has already seen.

Existing rows are left NULL: identity matching applies going forward only.

Revision ID: 014
Revises: 013
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signal_clusters",
        sa.Column("signal_hashes", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("signal_clusters", "signal_hashes")
