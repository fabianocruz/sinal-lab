"""Tests for scripts/reset_production.py — production database reset.

Validates row counting helpers, preserved content detection, the
execute_reset deletion logic, and the dry-run report.

Uses SQLite in-memory with StaticPool (same pattern as API tests).

Run: pytest scripts/tests/test_reset_production.py -v
"""

import logging
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.database.models.base import Base

from scripts.reset_production import (
    count_agent_content,
    count_evidence_items,
    execute_reset,
    fetch_preserved_content,
    print_dry_run_report,
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


def _insert_content(session, slug, agent_name=None, content_type="DATA_REPORT"):
    """Insert a minimal content_piece row."""
    session.execute(
        text(
            "INSERT INTO content_pieces (id, title, slug, body_md, content_type, "
            "agent_name, review_status) "
            "VALUES (:id, :title, :slug, :body_md, :content_type, :agent_name, :review_status)"
        ),
        {
            "id": uuid.uuid4().hex,
            "title": f"Test: {slug}",
            "slug": slug,
            "body_md": "Test body",
            "content_type": content_type,
            "agent_name": agent_name,
            "review_status": "published",
        },
    )
    session.flush()


def _insert_evidence(session, title="Evidence item"):
    """Insert a minimal evidence_items row."""
    import hashlib

    content_hash = hashlib.md5(f"{title}-{uuid.uuid4().hex}".encode()).hexdigest()
    session.execute(
        text(
            "INSERT INTO evidence_items (id, title, url, source_name, evidence_type, "
            "agent_name, content_hash, confidence) "
            "VALUES (:id, :title, :url, :source_name, :evidence_type, "
            ":agent_name, :content_hash, :confidence)"
        ),
        {
            "id": uuid.uuid4().hex,
            "title": title,
            "url": "https://example.com",
            "source_name": "test",
            "evidence_type": "article",
            "agent_name": "radar",
            "content_hash": content_hash,
            "confidence": 0.5,
        },
    )
    session.flush()


def _count_content(session) -> int:
    """Return total row count in content_pieces."""
    return session.execute(text("SELECT COUNT(*) FROM content_pieces")).scalar()


def _count_evidence(session) -> int:
    """Return total row count in evidence_items."""
    return session.execute(text("SELECT COUNT(*) FROM evidence_items")).scalar()


# ---------------------------------------------------------------------------
# count_evidence_items()
# ---------------------------------------------------------------------------


def test_count_evidence_items_empty(session):
    """Returns 0 on empty table."""
    assert count_evidence_items(session) == 0


def test_count_evidence_items_with_rows(session):
    """Returns correct count after inserting rows."""
    _insert_evidence(session, "Item 1")
    _insert_evidence(session, "Item 2")
    _insert_evidence(session, "Item 3")
    session.commit()

    assert count_evidence_items(session) == 3


# ---------------------------------------------------------------------------
# count_agent_content()
# ---------------------------------------------------------------------------


def test_count_agent_content_empty(session):
    """Returns 0 on empty table."""
    assert count_agent_content(session) == 0


def test_count_agent_content_only_agent_rows(session):
    """Counts only rows where agent_name IS NOT NULL."""
    _insert_content(session, "agent-1", agent_name="sintese")
    _insert_content(session, "agent-2", agent_name="radar")
    _insert_content(session, "admin-1", agent_name=None)  # should NOT count
    session.commit()

    assert count_agent_content(session) == 2


# ---------------------------------------------------------------------------
# fetch_preserved_content()
# ---------------------------------------------------------------------------


def test_fetch_preserved_content_article_type(session):
    """ARTICLE content_type pieces are preserved."""
    _insert_content(session, "admin-article", content_type="ARTICLE", agent_name=None)
    session.commit()

    preserved = fetch_preserved_content(session)

    assert len(preserved) == 1
    assert preserved[0][1] == "admin-article"  # slug


def test_fetch_preserved_content_no_agent_provenance(session):
    """Pieces with no agent_name AND no agent_run_id are preserved."""
    _insert_content(session, "manual-piece", agent_name=None, content_type="DATA_REPORT")
    session.commit()

    preserved = fetch_preserved_content(session)

    assert len(preserved) == 1
    assert preserved[0][1] == "manual-piece"


def test_fetch_preserved_excludes_agent_content(session):
    """Agent-generated pieces are NOT in the preserved list."""
    _insert_content(session, "agent-piece", agent_name="sintese")
    _insert_content(session, "admin-piece", agent_name=None, content_type="ARTICLE")
    session.commit()

    preserved = fetch_preserved_content(session)

    slugs = [p[1] for p in preserved]
    assert "admin-piece" in slugs
    assert "agent-piece" not in slugs


def test_fetch_preserved_ordered_by_title(session):
    """Preserved content is ordered alphabetically by title."""
    _insert_content(session, "z-piece", agent_name=None, content_type="ARTICLE")
    _insert_content(session, "a-piece", agent_name=None, content_type="ARTICLE")
    session.commit()

    preserved = fetch_preserved_content(session)

    # Titles are "Test: a-piece" and "Test: z-piece"
    assert preserved[0][1] == "a-piece"
    assert preserved[1][1] == "z-piece"


def test_fetch_preserved_empty_db(session):
    """Returns empty list when database is empty."""
    preserved = fetch_preserved_content(session)
    assert preserved == []


# ---------------------------------------------------------------------------
# execute_reset()
# ---------------------------------------------------------------------------


def test_execute_reset_deletes_evidence_items(session):
    """execute_reset clears all evidence_items."""
    _insert_evidence(session, "Evidence 1")
    _insert_evidence(session, "Evidence 2")
    session.commit()

    logger = logging.getLogger("test_reset")
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    assert _count_evidence(session) == 0


def test_execute_reset_deletes_agent_content_only(session):
    """execute_reset deletes agent-generated content but preserves admin content."""
    _insert_content(session, "agent-1", agent_name="sintese")
    _insert_content(session, "agent-2", agent_name="radar")
    _insert_content(session, "admin-1", agent_name=None, content_type="ARTICLE")
    _insert_content(session, "admin-2", agent_name=None, content_type="DATA_REPORT")
    session.commit()

    logger = logging.getLogger("test_reset")
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    # Agent content deleted, admin content preserved
    assert _count_content(session) == 2
    remaining = session.execute(
        text("SELECT slug FROM content_pieces ORDER BY slug")
    ).fetchall()
    slugs = [r[0] for r in remaining]
    assert "admin-1" in slugs
    assert "admin-2" in slugs
    assert "agent-1" not in slugs
    assert "agent-2" not in slugs


def test_execute_reset_preserves_article_type(session):
    """Pieces with content_type='ARTICLE' survive even if they had agent provenance quirks."""
    # This edge case: ARTICLE type with no agent_name — always preserved
    _insert_content(session, "article-safe", agent_name=None, content_type="ARTICLE")
    session.commit()

    logger = logging.getLogger("test_reset")
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    assert _count_content(session) == 1


def test_execute_reset_on_empty_db(session):
    """execute_reset succeeds on an empty database."""
    logger = logging.getLogger("test_reset")
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    assert _count_content(session) == 0
    assert _count_evidence(session) == 0


def test_execute_reset_skips_missing_agent_runs(session):
    """When has_agent_runs=False, the agent_runs DELETE is skipped."""
    _insert_evidence(session)
    session.commit()

    logger = logging.getLogger("test_reset")
    # Should not raise even though agent_runs table may not exist in logic
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    assert _count_evidence(session) == 0


def test_execute_reset_skips_missing_funding_rounds(session):
    """When has_funding_rounds=False, the funding_rounds DELETE is skipped."""
    _insert_evidence(session)
    session.commit()

    logger = logging.getLogger("test_reset")
    execute_reset(session, logger, has_agent_runs=False, has_funding_rounds=False)

    assert _count_evidence(session) == 0


# ---------------------------------------------------------------------------
# print_dry_run_report() — smoke test
# ---------------------------------------------------------------------------


def test_dry_run_report_does_not_modify_data(session, capsys):
    """Dry run report prints counts without deleting anything."""
    _insert_content(session, "agent-1", agent_name="sintese")
    _insert_content(session, "admin-1", agent_name=None, content_type="ARTICLE")
    _insert_evidence(session, "Evidence 1")
    session.commit()

    logger = logging.getLogger("test_reset")
    print_dry_run_report(session, logger, has_agent_runs=False, has_funding_rounds=False)

    # Data should still be intact
    assert _count_content(session) == 2
    assert _count_evidence(session) == 1

    # Verify output mentions counts
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "1 rows" in captured.out  # evidence_items
    assert "preserving 1 admin article" in captured.out


def test_dry_run_report_no_preserved(session, capsys):
    """Dry run shows 'no admin articles' when none exist."""
    _insert_content(session, "agent-1", agent_name="sintese")
    session.commit()

    logger = logging.getLogger("test_reset")
    print_dry_run_report(session, logger, has_agent_runs=False, has_funding_rounds=False)

    captured = capsys.readouterr()
    assert "no admin articles to preserve" in captured.out


# ---------------------------------------------------------------------------
# parse_args()
# ---------------------------------------------------------------------------


def test_parse_args_dry_run(monkeypatch):
    """--dry-run flag is parsed correctly."""
    from scripts.reset_production import parse_args

    monkeypatch.setattr("sys.argv", ["reset_production.py", "--dry-run"])
    args = parse_args()
    assert args.dry_run is True
    assert args.confirm is False


def test_parse_args_confirm(monkeypatch):
    """--confirm flag is parsed correctly."""
    from scripts.reset_production import parse_args

    monkeypatch.setattr("sys.argv", ["reset_production.py", "--confirm"])
    args = parse_args()
    assert args.confirm is True
    assert args.dry_run is False


def test_parse_args_verbose(monkeypatch):
    """--verbose flag is parsed correctly."""
    from scripts.reset_production import parse_args

    monkeypatch.setattr("sys.argv", ["reset_production.py", "--dry-run", "--verbose"])
    args = parse_args()
    assert args.verbose is True


# ---------------------------------------------------------------------------
# main() — CLI smoke tests
# ---------------------------------------------------------------------------


def test_main_requires_flag(monkeypatch):
    """main() exits with code 2 when neither --dry-run nor --confirm is passed."""
    from scripts.reset_production import main

    monkeypatch.setattr("sys.argv", ["reset_production.py"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2


def test_main_dry_run_calls_report(monkeypatch):
    """main() with --dry-run calls print_dry_run_report (not execute_reset)."""
    import scripts.reset_production as mod
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr("sys.argv", ["reset_production.py", "--dry-run"])
    monkeypatch.setattr(mod, "DATABASE_URL", "sqlite:///:memory:")

    mock_report = MagicMock()
    mock_execute = MagicMock()
    mock_table_exists = MagicMock(return_value=False)

    with patch.object(mod, "print_dry_run_report", mock_report), \
         patch.object(mod, "execute_reset", mock_execute), \
         patch.object(mod, "table_exists", mock_table_exists), \
         patch.object(mod, "create_engine") as mock_engine:
        mock_session = MagicMock()
        mock_engine.return_value = MagicMock()
        monkeypatch.setattr(mod, "sessionmaker", lambda **kw: lambda: mock_session)

        mod.main()

    mock_report.assert_called_once()
    mock_execute.assert_not_called()


def test_main_confirm_calls_execute(monkeypatch):
    """main() with --confirm calls execute_reset (not print_dry_run_report)."""
    import scripts.reset_production as mod
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr("sys.argv", ["reset_production.py", "--confirm"])
    monkeypatch.setattr(mod, "DATABASE_URL", "sqlite:///:memory:")

    mock_report = MagicMock()
    mock_execute = MagicMock()
    mock_table_exists = MagicMock(return_value=False)
    mock_fetch = MagicMock(return_value=[])

    with patch.object(mod, "print_dry_run_report", mock_report), \
         patch.object(mod, "execute_reset", mock_execute), \
         patch.object(mod, "table_exists", mock_table_exists), \
         patch.object(mod, "fetch_preserved_content", mock_fetch), \
         patch.object(mod, "create_engine") as mock_engine:
        mock_session = MagicMock()
        mock_engine.return_value = MagicMock()
        monkeypatch.setattr(mod, "sessionmaker", lambda **kw: lambda: mock_session)

        mod.main()

    mock_execute.assert_called_once()
    mock_report.assert_not_called()
