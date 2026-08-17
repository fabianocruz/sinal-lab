"""Tests for cluster identity matching by signal membership.

Uses SQLite in-memory with StaticPool, matching the convention in the other
persistence tests.

Run: pytest apps/agents/base/tests/test_cluster_identity.py -v
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.base.cluster_identity import (
    MEMBERSHIP_OVERLAP_THRESHOLD,
    MIN_SHARED_SIGNALS,
    find_cluster_by_membership,
)
from packages.database.models.base import Base
from packages.database.models.signal_cluster import SignalCluster

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _hashes(n: int, offset: int = 0) -> List[str]:
    return [f"hash{i + offset:04d}" for i in range(n)]


def _add_cluster(
    db,
    name: str,
    signal_hashes: Optional[List[str]],
    week: int = 17,
    year: int = 2026,
) -> SignalCluster:
    cluster = SignalCluster(
        id=uuid.uuid4(),
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{year}-w{week:02d}",
        theme="AI",
        signal_count=len(signal_hashes or []),
        signal_hashes=signal_hashes,
        week_number=week,
        year=year,
        created_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
    )
    db.add(cluster)
    db.commit()
    return cluster


class TestFindClusterByMembership:
    def test_no_clusters_returns_none(self, db_session):
        assert find_cluster_by_membership(db_session, set(_hashes(10)), 2026, 17) is None

    def test_identical_membership_matches(self, db_session):
        stored = _hashes(10)
        _add_cluster(db_session, "Original", stored)

        match = find_cluster_by_membership(db_session, set(stored), 2026, 17)

        assert match is not None
        assert match.name == "Original"

    def test_superset_matches_the_smaller_stored_cluster(self, db_session):
        """The pool grows during the week; a later run holds a superset."""
        _add_cluster(db_session, "Original", _hashes(10))

        grown = set(_hashes(10)) | set(_hashes(6, offset=500))
        match = find_cluster_by_membership(db_session, grown, 2026, 17)

        assert match is not None

    def test_disjoint_membership_does_not_match(self, db_session):
        _add_cluster(db_session, "Original", _hashes(10))

        match = find_cluster_by_membership(db_session, set(_hashes(10, offset=900)), 2026, 17)

        assert match is None

    def test_overlap_below_threshold_does_not_match(self, db_session):
        """Half-shared is not the same bucket at the default threshold."""
        assert MEMBERSHIP_OVERLAP_THRESHOLD > 0.5
        _add_cluster(db_session, "Original", _hashes(20))

        incoming = set(_hashes(10)) | set(_hashes(10, offset=900))
        match = find_cluster_by_membership(db_session, incoming, 2026, 17)

        assert match is None

    def test_shared_count_below_floor_does_not_match(self, db_session):
        """Small clusters sharing a couple of posts must stay separate."""
        _add_cluster(db_session, "Tiny", _hashes(4))

        match = find_cluster_by_membership(db_session, set(_hashes(4)), 2026, 17)

        assert match is None, f"needs at least {MIN_SHARED_SIGNALS} shared signals"

    def test_other_week_is_never_matched(self, db_session):
        """Week boundaries deliberately start a fresh identity."""
        stored = _hashes(10)
        _add_cluster(db_session, "Week 17", stored, week=17)

        assert find_cluster_by_membership(db_session, set(stored), 2026, 18) is None

    def test_rows_without_recorded_membership_are_skipped(self, db_session):
        """Clusters written before migration 014 have NULL signal_hashes."""
        _add_cluster(db_session, "Legacy", None)

        assert find_cluster_by_membership(db_session, set(_hashes(10)), 2026, 17) is None

    def test_best_candidate_wins(self, db_session):
        """With several overlapping clusters, the closest one is chosen."""
        stored = _hashes(20)
        _add_cluster(db_session, "Partial", stored[:12] + _hashes(8, offset=700))
        _add_cluster(db_session, "Exact", stored)

        match = find_cluster_by_membership(db_session, set(stored), 2026, 17)

        assert match is not None
        assert match.name == "Exact"

    def test_incoming_below_floor_returns_none(self, db_session):
        """An incoming cluster too small to judge is never merged."""
        _add_cluster(db_session, "Original", _hashes(50))

        match = find_cluster_by_membership(db_session, set(_hashes(3)), 2026, 17)

        assert match is None
