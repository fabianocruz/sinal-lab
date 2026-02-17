"""Tests for the evidence writer module.

Tests persist_evidence_item, persist_evidence_batch, and persist_raw_items
using an in-memory SQLite database.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.agents.base.evidence import EvidenceItem, EvidenceType
from packages.database.models.base import Base
from packages.database.models.evidence_item import EvidenceItemDB

from apps.agents.base.evidence_writer import (
    persist_evidence_item,
    persist_evidence_batch,
    persist_raw_items,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Provide a transactional database session for tests."""
    factory = sessionmaker(bind=engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


def _make_evidence(
    title: str = "Show HN: New AI Framework",
    url: str = "https://news.ycombinator.com/item?id=12345",
    source_name: str = "hackernews",
    evidence_type: EvidenceType = EvidenceType.ARTICLE,
    agent_name: str = "sintese",
    confidence: float = 0.7,
    content_hash: Optional[str] = None,
) -> EvidenceItem:
    """Build a minimal EvidenceItem for testing."""
    item = EvidenceItem(
        title=title,
        url=url,
        source_name=source_name,
        evidence_type=evidence_type,
        agent_name=agent_name,
        confidence=confidence,
    )
    if content_hash:
        item.content_hash = content_hash
    return item


# ---------------------------------------------------------------------------
# TestPersistEvidenceItem
# ---------------------------------------------------------------------------


class TestPersistEvidenceItem:
    """Tests for persist_evidence_item()."""

    def test_inserts_new_item(self, session: Session):
        item = _make_evidence()

        persist_evidence_item(session, item)
        session.commit()

        count = session.query(EvidenceItemDB).count()
        assert count == 1

    def test_maps_all_fields(self, session: Session):
        item = _make_evidence(
            title="Test Title",
            url="https://example.com/test",
            source_name="test-source",
            evidence_type=EvidenceType.REPO,
            agent_name="radar",
            confidence=0.85,
        )
        item.summary = "A test summary."
        item.author = "author-1"
        item.tags = ["ai", "ml"]
        item.territory = "Brazil"
        item.metrics = {"stars": 100}
        item.raw_data = {"lang": "Python"}

        persist_evidence_item(session, item)
        session.commit()

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.title == "Test Title"
        assert db_item.url == "https://example.com/test"
        assert db_item.source_name == "test-source"
        assert db_item.evidence_type == "repo"
        assert db_item.agent_name == "radar"
        assert db_item.confidence == pytest.approx(0.85, abs=0.01)
        assert db_item.summary == "A test summary."
        assert db_item.author == "author-1"
        assert db_item.tags == ["ai", "ml"]
        assert db_item.territory == "Brazil"
        assert db_item.metrics == {"stars": 100}
        assert db_item.raw_data == {"lang": "Python"}

    def test_upserts_by_content_hash(self, session: Session):
        """Two items with the same content_hash → upsert, not duplicate."""
        item1 = _make_evidence(title="Original", url="https://example.com/1")
        persist_evidence_item(session, item1)
        session.commit()

        item2 = _make_evidence(title="Updated", url="https://example.com/1")
        # Same URL → same content_hash
        assert item2.content_hash == item1.content_hash

        persist_evidence_item(session, item2, confidence_wins=True)
        session.commit()

        count = session.query(EvidenceItemDB).count()
        assert count == 1

    def test_skips_lower_confidence(self, session: Session):
        """If existing has higher confidence, skip the update."""
        item_high = _make_evidence(confidence=0.9, url="https://example.com/same")
        persist_evidence_item(session, item_high)
        session.commit()

        item_low = _make_evidence(
            title="Should Not Update",
            confidence=0.3,
            url="https://example.com/same",
        )
        persist_evidence_item(session, item_low)
        session.commit()

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.confidence == pytest.approx(0.9, abs=0.01)
        assert db_item.title != "Should Not Update"

    def test_updates_higher_confidence(self, session: Session):
        """If new confidence is higher, update the record."""
        item_low = _make_evidence(
            title="Old Title", confidence=0.3, url="https://example.com/same"
        )
        persist_evidence_item(session, item_low)
        session.commit()

        item_high = _make_evidence(
            title="New Title", confidence=0.9, url="https://example.com/same"
        )
        persist_evidence_item(session, item_high)
        session.commit()

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.confidence == pytest.approx(0.9, abs=0.01)
        assert db_item.title == "New Title"

    def test_sets_collector_run_id(self, session: Session):
        item = _make_evidence()

        persist_evidence_item(session, item, collector_run_id="run-abc-123")
        session.commit()

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.collector_run_id == "run-abc-123"

    def test_content_hash_from_url(self, session: Session):
        """content_hash is auto-computed from URL by EvidenceItem.__post_init__."""
        item = _make_evidence(url="https://unique-url.com/test")

        persist_evidence_item(session, item)
        session.commit()

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.content_hash == item.content_hash
        assert len(db_item.content_hash) == 32  # MD5 hex digest


# ---------------------------------------------------------------------------
# TestPersistEvidenceBatch
# ---------------------------------------------------------------------------


class TestPersistEvidenceBatch:
    """Tests for persist_evidence_batch()."""

    def test_batch_insert(self, session: Session):
        items = [
            _make_evidence(url=f"https://example.com/{i}") for i in range(5)
        ]

        stats = persist_evidence_batch(session, items)

        assert stats["inserted"] == 5
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
        assert session.query(EvidenceItemDB).count() == 5

    def test_returns_stats(self, session: Session):
        items = [_make_evidence()]

        stats = persist_evidence_batch(session, items)

        assert "inserted" in stats
        assert "updated" in stats
        assert "skipped" in stats

    def test_handles_duplicates(self, session: Session):
        """Duplicate content_hash items in same batch → first wins."""
        item1 = _make_evidence(title="First", url="https://example.com/dup")
        item2 = _make_evidence(title="Second", url="https://example.com/dup")

        stats = persist_evidence_batch(session, [item1, item2])

        assert session.query(EvidenceItemDB).count() == 1

    def test_empty_list(self, session: Session):
        stats = persist_evidence_batch(session, [])

        assert stats == {"inserted": 0, "updated": 0, "skipped": 0}

    def test_mixed_insert_update_skip(self, session: Session):
        """Pre-existing item with medium confidence, then batch with high and low."""
        # Pre-insert with confidence 0.5
        existing = _make_evidence(
            title="Existing", url="https://example.com/existing", confidence=0.5
        )
        persist_evidence_item(session, existing)
        session.commit()

        # Batch: new item, higher-confidence update, lower-confidence skip
        new_item = _make_evidence(url="https://example.com/new", confidence=0.6)
        update_item = _make_evidence(
            title="Updated", url="https://example.com/existing", confidence=0.9
        )
        skip_item = _make_evidence(
            title="Skipped", url="https://example.com/existing", confidence=0.1
        )
        # Note: update_item and skip_item have same hash → only one of them
        # will be processed. Let's use different URLs for a cleaner test.

        # Pre-insert a second existing item
        existing2 = _make_evidence(
            title="Existing2", url="https://example.com/existing2", confidence=0.8
        )
        persist_evidence_item(session, existing2)
        session.commit()

        batch = [
            new_item,
            _make_evidence(
                title="Higher", url="https://example.com/existing", confidence=0.9
            ),
            _make_evidence(
                title="Lower", url="https://example.com/existing2", confidence=0.1
            ),
        ]

        stats = persist_evidence_batch(session, batch)

        assert stats["inserted"] == 1  # new_item
        assert stats["updated"] == 1  # higher confidence
        assert stats["skipped"] == 1  # lower confidence

    def test_passes_collector_run_id(self, session: Session):
        items = [_make_evidence(url=f"https://example.com/{i}") for i in range(2)]

        persist_evidence_batch(session, items, collector_run_id="batch-run-001")

        db_items = session.query(EvidenceItemDB).all()
        for db_item in db_items:
            assert db_item.collector_run_id == "batch-run-001"


# ---------------------------------------------------------------------------
# TestPersistRawItems
# ---------------------------------------------------------------------------


class TestPersistRawItems:
    """Tests for persist_raw_items()."""

    def test_normalizes_feed_items(self, session: Session):
        from apps.agents.sintese.collector import FeedItem

        feed_item = FeedItem(
            title="Test Article",
            url="https://blog.example.com/article",
            source_name="techblog",
        )

        stats = persist_raw_items(session, [feed_item], agent_name="sintese")

        assert stats["inserted"] == 1
        db_item = session.query(EvidenceItemDB).first()
        assert db_item.evidence_type == "article"

    def test_normalizes_trend_signals(self, session: Session):
        from apps.agents.radar.collector import TrendSignal

        signal = TrendSignal(
            title="Trending Repo",
            url="https://github.com/test/repo",
            source_name="github-trending",
            source_type="github",
        )

        stats = persist_raw_items(session, [signal], agent_name="radar")

        assert stats["inserted"] == 1
        db_item = session.query(EvidenceItemDB).first()
        assert db_item.evidence_type == "repo"

    def test_normalizes_funding_events(self, session: Session):
        from apps.agents.funding.collector import FundingEvent

        event = FundingEvent(
            company_name="TestCo",
            round_type="seed",
            source_url="https://crunchbase.com/funding/1",
            source_name="crunchbase",
        )

        stats = persist_raw_items(session, [event], agent_name="funding")

        assert stats["inserted"] == 1
        db_item = session.query(EvidenceItemDB).first()
        assert db_item.evidence_type == "funding_event"

    def test_raises_on_unknown_type(self, session: Session):
        with pytest.raises(ValueError, match="Unknown item type"):
            persist_raw_items(session, ["not a valid item"], agent_name="test")

    def test_passes_collector_run_id(self, session: Session):
        from apps.agents.sintese.collector import FeedItem

        feed_item = FeedItem(
            title="Test",
            url="https://example.com/test",
            source_name="test",
        )

        persist_raw_items(
            session, [feed_item], agent_name="sintese",
            collector_run_id="raw-run-001",
        )

        db_item = session.query(EvidenceItemDB).first()
        assert db_item.collector_run_id == "raw-run-001"

    def test_empty_list(self, session: Session):
        stats = persist_raw_items(session, [], agent_name="test")

        assert stats == {"inserted": 0, "updated": 0, "skipped": 0}
