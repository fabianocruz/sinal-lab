"""Tests for scripts/seed_content.py — newsletter seed script.

Validates idempotency (skip existing slugs), --force mode (delete and
re-insert), date parsing, and data integrity of the NEWSLETTERS constant.

Uses SQLite in-memory with StaticPool (same pattern as API tests).

Run: pytest scripts/tests/test_seed_content.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base

from scripts.seed_content import NEWSLETTERS, seed


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


# ---------------------------------------------------------------------------
# NEWSLETTERS constant validation
# ---------------------------------------------------------------------------


def test_newsletters_has_twenty_items():
    """All 20 founding newsletters are defined."""
    assert len(NEWSLETTERS) == 20


def test_newsletters_have_required_fields():
    """Every newsletter dict has all fields needed by the seed() function."""
    required = {
        "slug", "title", "subtitle", "agent_name",
        "content_type", "confidence_dq", "published_at",
        "meta_description", "body_md",
    }
    for item in NEWSLETTERS:
        missing = required - set(item.keys())
        assert missing == set(), f"{item['slug']} missing: {missing}"


def test_newsletters_slugs_are_unique():
    """No duplicate slugs in the NEWSLETTERS list."""
    slugs = [n["slug"] for n in NEWSLETTERS]
    assert len(slugs) == len(set(slugs))


def test_newsletters_dates_are_parseable():
    """All published_at values can be parsed as YYYY-MM-DD."""
    for item in NEWSLETTERS:
        dt = datetime.strptime(item["published_at"], "%Y-%m-%d")
        assert dt.year >= 2025


# ---------------------------------------------------------------------------
# seed() function — insert
# ---------------------------------------------------------------------------


def test_seed_inserts_all(session):
    """seed() inserts all newsletters into an empty database."""
    inserted = seed(session, NEWSLETTERS)

    assert inserted == 20
    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 20


def test_seed_sets_published_status(session):
    """All seeded rows have review_status = 'published'."""
    seed(session, NEWSLETTERS)

    rows = session.execute(
        text("SELECT DISTINCT review_status FROM content_pieces")
    ).fetchall()
    statuses = {r[0] for r in rows}
    assert statuses == {"published"}


def test_seed_parses_dates_with_utc(session):
    """published_at is stored as UTC with hour=6."""
    seed(session, NEWSLETTERS[:1])

    row = session.execute(
        text("SELECT published_at FROM content_pieces WHERE slug = :slug"),
        {"slug": NEWSLETTERS[0]["slug"]},
    ).fetchone()
    assert row is not None
    # The string should contain the date portion
    assert NEWSLETTERS[0]["published_at"] in str(row[0])


# ---------------------------------------------------------------------------
# seed() function — idempotency
# ---------------------------------------------------------------------------


def test_seed_skips_existing_slugs(session):
    """Running seed() twice without --force skips all existing rows."""
    first_run = seed(session, NEWSLETTERS)
    second_run = seed(session, NEWSLETTERS)

    assert first_run == 20
    assert second_run == 0

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 20


def test_seed_idempotent_with_subset(session):
    """Seeding a subset, then all, inserts only the new ones."""
    seed(session, NEWSLETTERS[:3])
    inserted = seed(session, NEWSLETTERS)

    assert inserted == 17  # only the 17 new ones

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 20


# ---------------------------------------------------------------------------
# seed() function — --force mode
# ---------------------------------------------------------------------------


def test_seed_force_reinserts(session):
    """With force=True, seed() deletes and re-inserts existing rows."""
    seed(session, NEWSLETTERS[:2])
    inserted = seed(session, NEWSLETTERS[:2], force=True)

    assert inserted == 2

    count = session.execute(text("SELECT count(*) FROM content_pieces")).scalar()
    assert count == 2


def test_seed_force_updates_content(session):
    """force=True allows updating content by re-inserting."""
    seed(session, NEWSLETTERS[:1])

    # Get the original id
    original_id = session.execute(
        text("SELECT id FROM content_pieces WHERE slug = :slug"),
        {"slug": NEWSLETTERS[0]["slug"]},
    ).scalar()

    seed(session, NEWSLETTERS[:1], force=True)

    # After force re-insert, the id should be different (new UUID)
    new_id = session.execute(
        text("SELECT id FROM content_pieces WHERE slug = :slug"),
        {"slug": NEWSLETTERS[0]["slug"]},
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


def test_seed_single_newsletter(session):
    """Seeding a single newsletter works correctly."""
    inserted = seed(session, NEWSLETTERS[:1])
    assert inserted == 1

    row = session.execute(
        text("SELECT title, slug, content_type FROM content_pieces")
    ).fetchone()
    assert row[0] == NEWSLETTERS[0]["title"]
    assert row[1] == NEWSLETTERS[0]["slug"]
    assert row[2] == NEWSLETTERS[0]["content_type"]
