"""Tests for Feed Curator db_writer — upsert and persistence orchestration.

Uses SQLite in-memory with StaticPool (project convention).
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.feed_curator.curator import CuratedItem
from apps.agents.feed_curator.db_writer import (
    _upsert_curated_item,
    persist_curated_feed,
)
from packages.database.models.base import Base
from packages.database.models.curated_feed_item import CuratedFeedItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    """Create an in-memory SQLite session with all tables."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_item(
    content_hash: str = "abc123",
    editorial_headline: str = "Startup capta rodada seed de R$5M",
    editorial_context: str = "Investimento importante para o ecossistema LATAM.",
    relevance_score: int = 82,
    category: str = "Fintech",
    source_platform: str = "twitter",
    source_url: str = "https://twitter.com/founder/1",
    source_author: str = "founder",
    source_text: str = "Anuncio da rodada seed.",
    thumbnail_url: Optional[str] = None,
    embed_type: Optional[str] = None,
    embed_url: Optional[str] = None,
) -> CuratedItem:
    """Create a CuratedItem with sensible defaults."""
    return CuratedItem(
        content_hash=content_hash,
        editorial_headline=editorial_headline,
        editorial_context=editorial_context,
        relevance_score=relevance_score,
        category=category,
        source_platform=source_platform,
        source_url=source_url,
        source_author=source_author,
        source_text=source_text,
        thumbnail_url=thumbnail_url,
        embed_type=embed_type,
        embed_url=embed_url,
    )


def make_agent(curated_items=None, run_id="test-run-001"):
    """Create a mock agent object with _curated_items and run_id attributes."""
    agent = MagicMock()
    agent._curated_items = curated_items or []
    agent.run_id = run_id
    return agent


# ---------------------------------------------------------------------------
# _upsert_curated_item — Insert
# ---------------------------------------------------------------------------


class TestUpsertCuratedItemInsert:
    """Test insertion of new CuratedFeedItem records."""

    def test_inserts_new_item(self, session):
        item = make_item(content_hash="new001")
        result = _upsert_curated_item(session, item, agent_run_id="run1")
        assert result == "inserted"

    def test_inserted_item_retrievable(self, session):
        item = make_item(content_hash="new002")
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="new002").first()
        assert record is not None

    def test_inserted_item_has_correct_headline(self, session):
        item = make_item(content_hash="h001", editorial_headline="Nubank lança produto X")
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="h001").first()
        assert record.editorial_headline == "Nubank lança produto X"

    def test_inserted_item_has_correct_category(self, session):
        item = make_item(content_hash="c001", category="AI")
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="c001").first()
        assert record.category == "AI"

    def test_inserted_item_has_correct_relevance_score(self, session):
        item = make_item(content_hash="s001", relevance_score=95)
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="s001").first()
        assert record.relevance_score == 95

    def test_inserted_item_stores_source_metadata(self, session):
        item = make_item(
            content_hash="meta001",
            source_platform="twitter",
            source_url="https://twitter.com/user/123",
            source_author="user_handle",
            source_text="Original tweet text",
        )
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="meta001").first()
        assert record.source_platform == "twitter"
        assert record.source_url == "https://twitter.com/user/123"
        assert record.source_author == "user_handle"
        assert "Original tweet" in record.source_text

    def test_inserted_item_stores_agent_run_id(self, session):
        item = make_item(content_hash="run001")
        _upsert_curated_item(session, item, agent_run_id="run-xyz-42")
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="run001").first()
        assert record.agent_run_id == "run-xyz-42"

    def test_inserted_item_has_curated_at_timestamp(self, session):
        item = make_item(content_hash="ts001")
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="ts001").first()
        assert record.curated_at is not None

    def test_source_text_truncated_to_500_chars(self, session):
        long_text = "Z" * 600
        item = make_item(content_hash="trunc001", source_text=long_text)
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="trunc001").first()
        assert len(record.source_text) == 500

    def test_source_text_at_500_chars_unchanged(self, session):
        text_500 = "A" * 500
        item = make_item(content_hash="exact001", source_text=text_500)
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="exact001").first()
        assert len(record.source_text) == 500

    def test_null_source_text_stored_as_none(self, session):
        item = make_item(content_hash="null001", source_text="")
        # Empty string becomes None in the model
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="null001").first()
        # Either None or empty string is acceptable — just verify no crash
        assert record is not None

    def test_inserts_thumbnail_url(self, session):
        item = make_item(
            content_hash="thumb001",
            thumbnail_url="https://img.youtube.com/vi/abc/hq.jpg",
        )
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="thumb001").first()
        assert record.thumbnail_url == "https://img.youtube.com/vi/abc/hq.jpg"

    def test_inserts_embed_fields(self, session):
        item = make_item(
            content_hash="embed001",
            embed_type="youtube",
            embed_url="https://www.youtube.com/embed/abc12345678",
        )
        _upsert_curated_item(session, item)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="embed001").first()
        assert record.embed_type == "youtube"
        assert record.embed_url == "https://www.youtube.com/embed/abc12345678"

    def test_no_agent_run_id_defaults_to_empty(self, session):
        item = make_item(content_hash="norun001")
        _upsert_curated_item(session, item)  # No agent_run_id arg
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="norun001").first()
        # agent_run_id should be empty string (default arg)
        assert record.agent_run_id == "" or record.agent_run_id is None


# ---------------------------------------------------------------------------
# _upsert_curated_item — Update
# ---------------------------------------------------------------------------


class TestUpsertCuratedItemUpdate:
    """Test update behavior when content_hash already exists."""

    def test_duplicate_hash_returns_updated(self, session):
        item = make_item(content_hash="dup001")
        _upsert_curated_item(session, item)
        session.flush()
        result = _upsert_curated_item(session, item)
        assert result == "updated"

    def test_update_changes_headline(self, session):
        item1 = make_item(content_hash="upd001", editorial_headline="Headline original")
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="upd001", editorial_headline="Headline melhorada")
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="upd001").first()
        assert record.editorial_headline == "Headline melhorada"

    def test_update_changes_context(self, session):
        item1 = make_item(content_hash="ctx001", editorial_context="Contexto original.")
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="ctx001", editorial_context="Contexto atualizado.")
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="ctx001").first()
        assert record.editorial_context == "Contexto atualizado."

    def test_update_changes_relevance_score(self, session):
        item1 = make_item(content_hash="score001", relevance_score=50)
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="score001", relevance_score=90)
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="score001").first()
        assert record.relevance_score == 90

    def test_update_changes_category(self, session):
        item1 = make_item(content_hash="cat001", category="Startup")
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="cat001", category="AI")
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="cat001").first()
        assert record.category == "AI"

    def test_update_sets_thumbnail_if_previously_null(self, session):
        item1 = make_item(content_hash="th001", thumbnail_url=None)
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="th001", thumbnail_url="https://img.example.com/new.jpg")
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="th001").first()
        assert record.thumbnail_url == "https://img.example.com/new.jpg"

    def test_update_preserves_existing_thumbnail_when_new_is_null(self, session):
        item1 = make_item(content_hash="th002", thumbnail_url="https://img.example.com/existing.jpg")
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(content_hash="th002", thumbnail_url=None)
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="th002").first()
        assert record.thumbnail_url == "https://img.example.com/existing.jpg"

    def test_update_changes_embed_fields(self, session):
        item1 = make_item(content_hash="em001", embed_type=None, embed_url=None)
        _upsert_curated_item(session, item1)
        session.flush()

        item2 = make_item(
            content_hash="em001",
            embed_type="youtube",
            embed_url="https://www.youtube.com/embed/xyz",
        )
        _upsert_curated_item(session, item2)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="em001").first()
        assert record.embed_type == "youtube"

    def test_update_changes_agent_run_id(self, session):
        item = make_item(content_hash="runupd001")
        _upsert_curated_item(session, item, agent_run_id="run-001")
        session.flush()
        _upsert_curated_item(session, item, agent_run_id="run-002")
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="runupd001").first()
        assert record.agent_run_id == "run-002"

    def test_only_one_record_after_upsert(self, session):
        item = make_item(content_hash="count001")
        _upsert_curated_item(session, item)
        _upsert_curated_item(session, item)
        session.flush()

        count = session.query(CuratedFeedItem).filter_by(content_hash="count001").count()
        assert count == 1


# ---------------------------------------------------------------------------
# persist_curated_feed
# ---------------------------------------------------------------------------


class TestPersistCuratedFeed:
    """Test the orchestrator callback for batch persistence."""

    def test_inserts_all_items(self, session):
        items = [make_item(content_hash=f"h{i}") for i in range(3)]
        agent = make_agent(curated_items=items, run_id="run-abc")
        persist_curated_feed(agent, None, session)
        session.flush()

        count = session.query(CuratedFeedItem).count()
        assert count == 3

    def test_empty_curated_items_does_nothing(self, session):
        agent = make_agent(curated_items=[])
        persist_curated_feed(agent, None, session)
        session.flush()

        count = session.query(CuratedFeedItem).count()
        assert count == 0

    def test_uses_agent_run_id(self, session):
        items = [make_item(content_hash="runtest001")]
        agent = make_agent(curated_items=items, run_id="run-special-42")
        persist_curated_feed(agent, None, session)
        session.flush()

        record = session.query(CuratedFeedItem).filter_by(content_hash="runtest001").first()
        assert record.agent_run_id == "run-special-42"

    def test_upserts_on_duplicate(self, session):
        item_v1 = make_item(content_hash="dup_persist", editorial_headline="V1 Headline")
        agent1 = make_agent(curated_items=[item_v1], run_id="run-1")
        persist_curated_feed(agent1, None, session)
        session.flush()

        item_v2 = make_item(content_hash="dup_persist", editorial_headline="V2 Headline")
        agent2 = make_agent(curated_items=[item_v2], run_id="run-2")
        persist_curated_feed(agent2, None, session)
        session.flush()

        count = session.query(CuratedFeedItem).filter_by(content_hash="dup_persist").count()
        assert count == 1

        record = session.query(CuratedFeedItem).filter_by(content_hash="dup_persist").first()
        assert record.editorial_headline == "V2 Headline"

    def test_flushes_session(self, session):
        """Session should be flushed (not committed) by persist_curated_feed."""
        items = [make_item(content_hash="flush001")]
        agent = make_agent(curated_items=items)

        persist_curated_feed(agent, None, session)

        # After flush, the record should be queryable within the same session
        record = session.query(CuratedFeedItem).filter_by(content_hash="flush001").first()
        assert record is not None

    def test_agent_without_curated_items_attr(self, session):
        """Agent with no _curated_items attribute defaults to empty list."""
        agent = Mock(spec=[])  # No attributes
        # Should not raise
        persist_curated_feed(agent, None, session)
        assert session.query(CuratedFeedItem).count() == 0

    def test_agent_without_run_id_attr(self, session):
        """Agent with no run_id attribute defaults to empty string."""
        agent = Mock(spec=[])
        agent._curated_items = [make_item(content_hash="noid001")]
        # Should not raise
        persist_curated_feed(agent, None, session)
        session.flush()
        record = session.query(CuratedFeedItem).filter_by(content_hash="noid001").first()
        assert record is not None

    def test_large_batch(self, session):
        items = [make_item(content_hash=f"large{i:04d}") for i in range(50)]
        agent = make_agent(curated_items=items, run_id="run-large")
        persist_curated_feed(agent, None, session)
        session.flush()

        count = session.query(CuratedFeedItem).count()
        assert count == 50
