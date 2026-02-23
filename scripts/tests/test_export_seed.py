"""Tests for scripts/export_seed.py — seed export to JSON.

Validates serialization of ContentPiece objects, summary building,
query filtering, and the overall export function.

Uses SQLite in-memory with StaticPool (same pattern as API tests).

Run: pytest scripts/tests/test_export_seed.py -v
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece

from scripts.export_seed import (
    KNOWN_AGENTS,
    build_summary,
    serialize_piece,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def session(engine):
    """Provide a database session for each test."""
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_piece(**overrides) -> ContentPiece:
    """Create a ContentPiece instance with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "slug": "test-slug",
        "title": "Test Title",
        "subtitle": "Test Subtitle",
        "body_md": "Test body markdown",
        "summary": "Test summary",
        "content_type": "DATA_REPORT",
        "agent_name": "sintese",
        "agent_run_id": "run-123",
        "confidence_dq": 4.5,
        "confidence_ac": 3.8,
        "sources": [{"url": "https://example.com", "title": "Example"}],
        "metadata_": {"edition": 1},
        "meta_description": "Test meta description",
        "published_at": datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        "review_status": "published",
        "author_name": None,
    }
    defaults.update(overrides)
    return ContentPiece(**defaults)


# ---------------------------------------------------------------------------
# KNOWN_AGENTS constant
# ---------------------------------------------------------------------------


def test_known_agents_has_five():
    """KNOWN_AGENTS lists all 5 content agent names."""
    assert len(KNOWN_AGENTS) == 5
    assert set(KNOWN_AGENTS) == {"sintese", "radar", "codigo", "funding", "mercado"}


# ---------------------------------------------------------------------------
# serialize_piece()
# ---------------------------------------------------------------------------


def test_serialize_piece_returns_all_fields():
    """Serialized output includes all expected keys."""
    piece = _make_piece()
    result = serialize_piece(piece)

    expected_keys = {
        "slug", "title", "subtitle", "body_md", "summary",
        "content_type", "agent_name", "agent_run_id",
        "confidence_dq", "confidence_ac", "sources", "metadata_",
        "meta_description", "published_at", "review_status", "author_name",
    }
    assert set(result.keys()) == expected_keys


def test_serialize_piece_preserves_values():
    """Serialized values match the original piece attributes."""
    piece = _make_piece(slug="my-slug", title="My Title", confidence_dq=4.2)
    result = serialize_piece(piece)

    assert result["slug"] == "my-slug"
    assert result["title"] == "My Title"
    assert result["confidence_dq"] == 4.2


def test_serialize_piece_published_at_as_iso_string():
    """published_at is serialized as an ISO 8601 string."""
    dt = datetime(2025, 12, 15, 10, 30, 0, tzinfo=timezone.utc)
    piece = _make_piece(published_at=dt)
    result = serialize_piece(piece)

    assert isinstance(result["published_at"], str)
    assert "2025-12-15" in result["published_at"]


def test_serialize_piece_none_published_at():
    """None published_at is serialized as None."""
    piece = _make_piece(published_at=None)
    result = serialize_piece(piece)

    assert result["published_at"] is None


def test_serialize_piece_none_sources_becomes_empty_list():
    """None sources is serialized as an empty list."""
    piece = _make_piece(sources=None)
    result = serialize_piece(piece)

    assert result["sources"] == []


def test_serialize_piece_none_metadata_becomes_empty_dict():
    """None metadata_ is serialized as an empty dict."""
    piece = _make_piece(metadata_=None)
    result = serialize_piece(piece)

    assert result["metadata_"] == {}


def test_serialize_piece_with_author_name():
    """author_name is included in serialized output."""
    piece = _make_piece(author_name="Fabiano Cruz")
    result = serialize_piece(piece)

    assert result["author_name"] == "Fabiano Cruz"


def test_serialize_piece_output_is_json_serializable():
    """The serialized dict can be round-tripped through JSON."""
    piece = _make_piece()
    result = serialize_piece(piece)

    serialized = json.dumps(result, ensure_ascii=False)
    deserialized = json.loads(serialized)
    assert deserialized["slug"] == result["slug"]


# ---------------------------------------------------------------------------
# build_summary()
# ---------------------------------------------------------------------------


def test_build_summary_with_all_agents():
    """Summary includes counts for all known agents."""
    pieces = [
        _make_piece(agent_name="sintese"),
        _make_piece(agent_name="sintese"),
        _make_piece(agent_name="radar"),
        _make_piece(agent_name="funding"),
    ]
    result = build_summary(pieces, "/tmp/test.json")

    assert "4 pieces" in result
    assert "2 sintese" in result
    assert "1 radar" in result
    assert "0 codigo" in result
    assert "1 funding" in result
    assert "0 mercado" in result
    assert "/tmp/test.json" in result


def test_build_summary_empty_list():
    """Summary handles empty piece list."""
    result = build_summary([], "output.json")
    assert "0 pieces" in result
    assert "0 sintese" in result


def test_build_summary_unknown_agent_not_broken_out():
    """Pieces with unknown agent_name are counted in total but not in breakdown."""
    pieces = [
        _make_piece(agent_name="unknown_agent"),
        _make_piece(agent_name="sintese"),
    ]
    result = build_summary(pieces, "out.json")

    assert "2 pieces" in result
    assert "1 sintese" in result
    assert "unknown_agent" not in result


def test_build_summary_none_agent_name():
    """Pieces with None agent_name (admin content) are handled gracefully."""
    pieces = [_make_piece(agent_name=None)]
    result = build_summary(pieces, "out.json")

    assert "1 pieces" in result


# ---------------------------------------------------------------------------
# query_pieces() — with real DB
# ---------------------------------------------------------------------------


def test_query_pieces_returns_only_published(session, monkeypatch):
    """query_pieces only returns pieces with review_status='published'."""
    import scripts.export_seed as mod

    # Insert published + draft pieces
    session.add(_make_piece(slug="pub-1", review_status="published"))
    session.add(_make_piece(slug="draft-1", review_status="draft"))
    session.add(_make_piece(slug="approved-1", review_status="approved"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    pieces = mod.query_pieces(agent_only=False)
    slugs = [p.slug for p in pieces]

    assert "pub-1" in slugs
    assert "draft-1" not in slugs
    assert "approved-1" not in slugs


def test_query_pieces_agent_only_filters_null_agent(session, monkeypatch):
    """agent_only=True excludes pieces with agent_name=None."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="agent-piece", agent_name="sintese", review_status="published"))
    session.add(_make_piece(slug="admin-piece", agent_name=None, review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    pieces = mod.query_pieces(agent_only=True)
    slugs = [p.slug for p in pieces]

    assert "agent-piece" in slugs
    assert "admin-piece" not in slugs


def test_query_pieces_ordered_by_published_at(session, monkeypatch):
    """Results are ordered by published_at ASC."""
    import scripts.export_seed as mod

    session.add(_make_piece(
        slug="newer",
        published_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
        review_status="published",
    ))
    session.add(_make_piece(
        slug="older",
        published_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
        review_status="published",
    ))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    pieces = mod.query_pieces(agent_only=False)
    assert pieces[0].slug == "older"
    assert pieces[1].slug == "newer"


# ---------------------------------------------------------------------------
# export() — writes JSON file
# ---------------------------------------------------------------------------


def test_export_writes_valid_json(session, monkeypatch, tmp_path):
    """export() writes a valid JSON file with the correct structure."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="export-test", review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "seed.json"
    pieces = mod.export(str(output_path), agent_only=False)

    assert len(pieces) == 1
    assert output_path.exists()

    data = json.loads(output_path.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["slug"] == "export-test"


def test_export_creates_parent_directories(session, monkeypatch, tmp_path):
    """export() creates parent directories if they don't exist."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="nested-test", review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "nested" / "deep" / "seed.json"
    pieces = mod.export(str(output_path))

    assert len(pieces) == 1
    assert output_path.exists()


def test_export_empty_db_writes_empty_array(session, monkeypatch, tmp_path):
    """export() writes an empty JSON array when no pieces match."""
    import scripts.export_seed as mod

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "empty.json"
    pieces = mod.export(str(output_path))

    assert len(pieces) == 0
    data = json.loads(output_path.read_text())
    assert data == []


def test_export_agent_only_filters(session, monkeypatch, tmp_path):
    """export() with agent_only=True excludes admin content."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="agent-piece", agent_name="sintese", review_status="published"))
    session.add(_make_piece(slug="admin-piece", agent_name=None, review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "filtered.json"
    pieces = mod.export(str(output_path), agent_only=True)

    assert len(pieces) == 1
    data = json.loads(output_path.read_text())
    assert data[0]["slug"] == "agent-piece"


def test_export_returns_content_piece_objects(session, monkeypatch, tmp_path):
    """export() returns a list of ContentPiece ORM instances."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="orm-test", review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "orm.json"
    pieces = mod.export(str(output_path))

    assert isinstance(pieces[0], ContentPiece)
    assert pieces[0].slug == "orm-test"


def test_export_roundtrip_preserves_data(session, monkeypatch, tmp_path):
    """Data exported to JSON can be loaded back with correct values."""
    import scripts.export_seed as mod

    piece = _make_piece(
        slug="roundtrip-test",
        title="Roundtrip Title",
        summary="Roundtrip summary",
        sources=[{"url": "https://example.com", "title": "Source"}],
        metadata_={"edition": 42},
        review_status="published",
    )
    session.add(piece)
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = tmp_path / "roundtrip.json"
    mod.export(str(output_path))

    data = json.loads(output_path.read_text())
    item = data[0]
    assert item["slug"] == "roundtrip-test"
    assert item["title"] == "Roundtrip Title"
    assert item["sources"] == [{"url": "https://example.com", "title": "Source"}]
    assert item["metadata_"] == {"edition": 42}


# ---------------------------------------------------------------------------
# main() — CLI smoke tests
# ---------------------------------------------------------------------------


def test_main_prints_summary(session, monkeypatch, tmp_path, capsys):
    """main() prints an export summary to stdout."""
    import scripts.export_seed as mod

    session.add(_make_piece(slug="main-test", agent_name="sintese", review_status="published"))
    session.commit()

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = str(tmp_path / "main.json")
    monkeypatch.setattr("sys.argv", ["export_seed.py", "--output", output_path])

    mod.main()

    captured = capsys.readouterr()
    assert "1 pieces" in captured.out
    assert "1 sintese" in captured.out


def test_main_no_pieces_prints_nothing_to_export(session, monkeypatch, tmp_path, capsys):
    """main() prints a clear message when no pieces are found."""
    import scripts.export_seed as mod

    monkeypatch.setattr(mod, "SessionLocal", lambda: session)

    output_path = str(tmp_path / "empty.json")
    monkeypatch.setattr("sys.argv", ["export_seed.py", "--output", output_path])

    mod.main()

    captured = capsys.readouterr()
    assert "No published pieces found" in captured.out
