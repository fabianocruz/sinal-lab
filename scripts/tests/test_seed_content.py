"""Tests for scripts/seed_content.py — JSON-based seed script.

Validates seed loading from JSON, idempotency (skip existing slugs),
--force mode (delete and re-insert), date parsing, and JSONB handling.

Uses SQLite in-memory with StaticPool (same pattern as API tests).

Run: pytest scripts/tests/test_seed_content.py -v
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base

from scripts.seed_content import _parse_published_at, load_seed_data, seed


# ---------------------------------------------------------------------------
# Sample data (mimics export_seed.py output)
# ---------------------------------------------------------------------------

SAMPLE_PIECES = [
    {
        "slug": "sinal-semanal-19",
        "title": "Sinal Semanal #19 — Teste de Seed",
        "subtitle": "TAMBEM: 5 rodadas mapeadas",
        "body_md": "Conteudo de teste para o seed.\n\nSegundo paragrafo.",
        "summary": "Resumo do sinal semanal 19.",
        "content_type": "DATA_REPORT",
        "agent_name": "sintese",
        "agent_run_id": "run-abc-123",
        "confidence_dq": 4.5,
        "confidence_ac": 3.8,
        "sources": [
            {"url": "https://example.com/a", "title": "Source A"},
        ],
        "metadata_": {"edition": 19, "items": []},
        "meta_description": "Descricao meta do sinal semanal 19.",
        "published_at": "2025-09-01T12:00:00+00:00",
        "review_status": "published",
        "author_name": None,
    },
    {
        "slug": "radar-week-1",
        "title": "Radar Week 1 — Tendencias da Semana",
        "subtitle": "TAMBEM: AI ganha tracao em fintechs",
        "body_md": "Conteudo de teste radar week 1.",
        "summary": "Resumo radar week 1.",
        "content_type": "ANALYSIS",
        "agent_name": "radar",
        "agent_run_id": "run-def-456",
        "confidence_dq": 3.0,
        "confidence_ac": 4.0,
        "sources": [],
        "metadata_": {"trends": []},
        "meta_description": "Descricao meta do radar week 1.",
        "published_at": "2025-09-01T12:00:00+00:00",
        "review_status": "published",
        "author_name": None,
    },
    {
        "slug": "codigo-week-1",
        "title": "Codigo Week 1 — Infraestrutura e Codigo",
        "subtitle": "TAMBEM: Rust cresce em startups",
        "body_md": "Conteudo de teste codigo week 1.",
        "summary": "Resumo codigo week 1.",
        "content_type": "ANALYSIS",
        "agent_name": "codigo",
        "agent_run_id": "run-ghi-789",
        "confidence_dq": None,
        "confidence_ac": None,
        "sources": [],
        "metadata_": {},
        "meta_description": "Descricao meta do codigo week 1.",
        "published_at": "2025-09-01T12:00:00+00:00",
        "review_status": "published",
        "author_name": None,
    },
]


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


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    """Write SAMPLE_PIECES to a temporary JSON file and return the path."""
    path = tmp_path / "seed_data.json"
    path.write_text(json.dumps(SAMPLE_PIECES, ensure_ascii=False, indent=2))
    return path


# ---------------------------------------------------------------------------
# SQLite compatibility — strip ::jsonb casts
# ---------------------------------------------------------------------------
# SQLite doesn't support ::jsonb casts, so we patch sqlalchemy.text at the
# module level to strip them before the SQL reaches the driver.


@pytest.fixture(autouse=True)
def _patch_text_for_sqlite(monkeypatch):
    """Replace ::jsonb casts in SQL strings so SQLite can execute them."""
    import scripts.seed_content as mod

    _original_text = text

    def _sqlite_text(sql):
        return _original_text(sql.replace("::jsonb", ""))

    monkeypatch.setattr(mod, "text", _sqlite_text)


# ---------------------------------------------------------------------------
# load_seed_data()
# ---------------------------------------------------------------------------


def test_load_seed_data_returns_list(seed_file):
    """load_seed_data() returns a list of dicts from a JSON file."""
    data = load_seed_data(seed_file)
    assert isinstance(data, list)
    assert len(data) == 3


def test_load_seed_data_preserves_fields(seed_file):
    """All fields from the JSON are preserved in loaded data."""
    data = load_seed_data(seed_file)
    first = data[0]
    assert first["slug"] == "sinal-semanal-19"
    assert first["agent_name"] == "sintese"
    assert first["confidence_dq"] == 4.5
    assert first["sources"] == [{"url": "https://example.com/a", "title": "Source A"}]
    assert first["metadata_"]["edition"] == 19


def test_load_seed_data_file_not_found():
    """load_seed_data() raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        load_seed_data(Path("/nonexistent/seed.json"))


def test_load_seed_data_invalid_json(tmp_path):
    """load_seed_data() raises JSONDecodeError for invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    with pytest.raises(json.JSONDecodeError):
        load_seed_data(bad_file)


def test_load_seed_data_not_array(tmp_path):
    """load_seed_data() raises ValueError if root is not an array."""
    obj_file = tmp_path / "obj.json"
    obj_file.write_text('{"key": "value"}')
    with pytest.raises(ValueError, match="Expected a JSON array"):
        load_seed_data(obj_file)


# ---------------------------------------------------------------------------
# _parse_published_at()
# ---------------------------------------------------------------------------


def test_parse_iso_with_timezone():
    """ISO 8601 with timezone is parsed correctly."""
    dt = _parse_published_at("2025-09-01T12:00:00+00:00")
    assert dt.year == 2025
    assert dt.month == 9
    assert dt.hour == 12
    assert dt.tzinfo is not None


def test_parse_bare_date():
    """Bare YYYY-MM-DD is parsed with hour=6 UTC."""
    dt = _parse_published_at("2025-09-01")
    assert dt.year == 2025
    assert dt.month == 9
    assert dt.day == 1
    assert dt.hour == 6
    assert dt.tzinfo == timezone.utc


def test_parse_none_returns_now():
    """None falls back to current UTC time."""
    dt = _parse_published_at(None)
    assert dt.tzinfo is not None
    # Should be within a few seconds of now
    delta = abs((datetime.now(timezone.utc) - dt).total_seconds())
    assert delta < 5


def test_parse_naive_datetime():
    """Naive datetime gets UTC timezone attached."""
    naive = datetime(2025, 6, 15, 10, 30)
    dt = _parse_published_at(naive)
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 10


def test_parse_aware_datetime_preserved():
    """Aware datetime is returned as-is."""
    aware = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
    dt = _parse_published_at(aware)
    assert dt is aware


# ---------------------------------------------------------------------------
# seed() — insert
# ---------------------------------------------------------------------------


def test_seed_inserts_all(session):
    """seed() inserts all pieces into an empty database."""
    inserted = seed(session, SAMPLE_PIECES)

    assert inserted == 3
    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 3


def test_seed_sets_published_status(session):
    """All seeded rows have review_status = 'published'."""
    seed(session, SAMPLE_PIECES)

    rows = session.execute(
        text("SELECT DISTINCT review_status FROM content_pieces")
    ).fetchall()
    statuses = {r[0] for r in rows}
    assert statuses == {"published"}


def test_seed_stores_correct_fields(session):
    """Inserted rows have all expected field values."""
    seed(session, SAMPLE_PIECES[:1])

    row = session.execute(
        text(
            "SELECT title, slug, content_type, agent_name, confidence_dq, confidence_ac "
            "FROM content_pieces WHERE slug = :slug"
        ),
        {"slug": "sinal-semanal-19"},
    ).fetchone()

    assert row[0] == "Sinal Semanal #19 — Teste de Seed"
    assert row[1] == "sinal-semanal-19"
    assert row[2] == "DATA_REPORT"
    assert row[3] == "sintese"
    assert row[4] == 4.5
    assert row[5] == 3.8


def test_seed_stores_agent_run_id(session):
    """agent_run_id is persisted from seed data."""
    seed(session, SAMPLE_PIECES[:1])

    row = session.execute(
        text("SELECT agent_run_id FROM content_pieces WHERE slug = :slug"),
        {"slug": "sinal-semanal-19"},
    ).fetchone()
    assert row[0] == "run-abc-123"


def test_seed_handles_null_confidence(session):
    """Pieces with None confidence values are inserted successfully."""
    seed(session, [SAMPLE_PIECES[2]])  # codigo has None confidence

    row = session.execute(
        text("SELECT confidence_dq, confidence_ac FROM content_pieces WHERE slug = :slug"),
        {"slug": "codigo-week-1"},
    ).fetchone()
    assert row[0] is None
    assert row[1] is None


# ---------------------------------------------------------------------------
# seed() — idempotency
# ---------------------------------------------------------------------------


def test_seed_skips_existing_slugs(session):
    """Running seed() twice without --force skips all existing rows."""
    first_run = seed(session, SAMPLE_PIECES)
    second_run = seed(session, SAMPLE_PIECES)

    assert first_run == 3
    assert second_run == 0

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 3


def test_seed_idempotent_with_subset(session):
    """Seeding a subset, then all, inserts only the new ones."""
    seed(session, SAMPLE_PIECES[:1])
    inserted = seed(session, SAMPLE_PIECES)

    assert inserted == 2  # only the 2 new ones

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 3


# ---------------------------------------------------------------------------
# seed() — --force mode
# ---------------------------------------------------------------------------


def test_seed_force_reinserts(session):
    """With force=True, seed() deletes and re-inserts existing rows."""
    seed(session, SAMPLE_PIECES[:2])
    inserted = seed(session, SAMPLE_PIECES[:2], force=True)

    assert inserted == 2

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 2


def test_seed_force_updates_content(session):
    """force=True allows updating content by re-inserting."""
    seed(session, SAMPLE_PIECES[:1])

    original_id = session.execute(
        text("SELECT id FROM content_pieces WHERE slug = :slug"),
        {"slug": SAMPLE_PIECES[0]["slug"]},
    ).scalar()

    seed(session, SAMPLE_PIECES[:1], force=True)

    new_id = session.execute(
        text("SELECT id FROM content_pieces WHERE slug = :slug"),
        {"slug": SAMPLE_PIECES[0]["slug"]},
    ).scalar()

    assert original_id != new_id


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_seed_empty_list(session):
    """Seeding an empty list inserts nothing."""
    inserted = seed(session, [])
    assert inserted == 0

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 0


def test_seed_single_piece(session):
    """Seeding a single piece works correctly."""
    inserted = seed(session, SAMPLE_PIECES[:1])
    assert inserted == 1

    row = session.execute(
        text("SELECT title, slug, content_type FROM content_pieces")
    ).fetchone()
    assert row[0] == SAMPLE_PIECES[0]["title"]
    assert row[1] == SAMPLE_PIECES[0]["slug"]
    assert row[2] == SAMPLE_PIECES[0]["content_type"]


def test_seed_minimal_piece(session):
    """A piece with only required fields (slug, title, body_md) inserts successfully."""
    minimal = [
        {
            "slug": "minimal-test",
            "title": "Minimal Test Piece",
            "body_md": "Just the basics.",
        }
    ]
    inserted = seed(session, minimal)
    assert inserted == 1

    row = session.execute(
        text("SELECT slug, title, content_type, agent_name FROM content_pieces")
    ).fetchone()
    assert row[0] == "minimal-test"
    assert row[1] == "Minimal Test Piece"
    assert row[2] == "DATA_REPORT"  # default
    assert row[3] is None  # no agent
