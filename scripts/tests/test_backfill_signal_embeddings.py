"""Tests for the social_signals embeddings backfill script."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.social_signals.similarity import reset_pgvector_cache
from packages.database.models.base import Base
from packages.database.models.social_signal import SocialSignal
from scripts.backfill_signal_embeddings import (
    _vector_literal,
    backfill,
    needs_backfill,
)

DIM = 1536


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    reset_pgvector_cache()
    yield sess
    sess.close()
    reset_pgvector_cache()


def _signal(text: str = "Startup levanta rodada", embedding=None) -> SocialSignal:
    return SocialSignal(
        id=uuid.uuid4(),
        content_hash=uuid.uuid4().hex,
        platform="twitter",
        author_handle="user1",
        text=text,
        post_url="https://twitter.com/u/1",
        theme="AI",
        published_at=datetime.now(timezone.utc),
        embedding_json=embedding,
    )


class TestNeedsBackfill:
    def test_none_needs_backfill(self):
        assert needs_backfill(None) is True

    def test_empty_needs_backfill(self):
        assert needs_backfill([]) is True

    def test_zero_vector_needs_backfill(self):
        """Zero vectors are what the module wrote without openai/sklearn."""
        assert needs_backfill([0.0] * DIM) is True

    def test_real_vector_does_not(self):
        vec = [0.0] * DIM
        vec[3] = 0.12
        assert needs_backfill(vec) is False


class TestVectorLiteral:
    def test_pgvector_literal_format(self):
        assert _vector_literal([0.1, -0.2, 1.0]) == "[0.1,-0.2,1.0]"


class TestBackfill:
    @patch("scripts.backfill_signal_embeddings.embed_texts")
    def test_embeds_missing_and_zero_rows_only(self, mock_embed, session):
        good = [0.0] * DIM
        good[0] = 0.5
        session.add(_signal("ja embedado", embedding=good))
        session.add(_signal("sem embedding", embedding=None))
        session.add(_signal("embedding zerado", embedding=[0.0] * DIM))
        session.flush()

        mock_embed.side_effect = lambda texts: [[0.1] * DIM for _ in texts]

        stats = backfill(session)

        assert stats == {
            "scanned": 3, "backfilled": 2, "skipped": 1, "vector_column": False,
        }
        rows = session.query(SocialSignal).all()
        assert all(any(r.embedding_json) for r in rows)

    @patch("scripts.backfill_signal_embeddings.embed_texts")
    def test_dry_run_writes_nothing(self, mock_embed, session):
        session.add(_signal("sem embedding", embedding=None))
        session.flush()

        stats = backfill(session, dry_run=True)

        assert stats["backfilled"] == 1
        mock_embed.assert_not_called()
        assert session.query(SocialSignal).one().embedding_json is None

    @patch("scripts.backfill_signal_embeddings.embed_texts", return_value=None)
    def test_aborts_loudly_without_openai(self, mock_embed, session):
        """Never write degraded vectors: unavailable OpenAI must raise."""
        session.add(_signal("sem embedding", embedding=None))
        session.flush()

        with pytest.raises(RuntimeError, match="OpenAI embeddings unavailable"):
            backfill(session)

        assert session.query(SocialSignal).one().embedding_json is None

    @patch("scripts.backfill_signal_embeddings.embed_texts")
    def test_batches_respect_batch_size(self, mock_embed, session):
        for i in range(5):
            session.add(_signal(f"sinal {i}", embedding=None))
        session.flush()

        calls: list = []

        def record(texts):
            calls.append(len(texts))
            return [[0.1] * DIM for _ in texts]

        mock_embed.side_effect = record

        stats = backfill(session, batch_size=2)

        assert stats["backfilled"] == 5
        assert calls == [2, 2, 1]
