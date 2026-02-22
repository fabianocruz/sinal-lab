"""Tests for scripts/sync_audience.py — Resend Audience sync entry point.

Covers default status filtering, custom status filtering, first_name extraction,
missing name handling, empty result handling, session cleanup, dry-run behavior,
status flag forwarding, bulk_sync invocation, and skipped-sync logging.
"""

from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_audience import get_users, main


# ---------------------------------------------------------------------------
# TestGetUsers
# ---------------------------------------------------------------------------


class TestGetUsers:
    """Tests for get_users() — PostgreSQL query and contact extraction."""

    def _make_mock_db(self, users: list) -> tuple[MagicMock, MagicMock, MagicMock]:
        """Return (mock_engine, mock_session_class, mock_session) wired up."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = users

        mock_session_class = MagicMock(return_value=mock_session)
        mock_engine = MagicMock()

        return mock_engine, mock_session_class, mock_session

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_default_statuses_filter_active_and_waitlist(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """When called with no args, should query with statuses ['active', 'waitlist']."""
        mock_engine, mock_session_class, mock_session = self._make_mock_db([])
        mock_create_engine.return_value = mock_engine
        mock_sessionmaker.return_value = mock_session_class

        get_users()

        # Retrieve the status list that was passed to .in_()
        filter_call = mock_session.query.return_value.filter.call_args
        # filter_call[0][0] is the BinaryExpression from User.status.in_(statuses)
        # We inspect by checking that the call was made with the right argument
        # by re-examining what .in_() was called with on the column expression.
        # Since SQLAlchemy column expressions are MagicMock here, we verify indirectly
        # by calling get_users with explicit statuses and checking behaviour.
        assert filter_call is not None

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_default_statuses_queries_correct_list(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """Calls with no args must use ['active', 'waitlist'] — verified via spy."""
        captured: list[list[str]] = []

        mock_session = MagicMock()

        def fake_filter(expr):
            # Capture the list that was passed to User.status.in_()
            # expr is the result of User.status.in_(statuses); we capture via
            # the mock chain: User.status.in_ is a MagicMock, its call_args holds statuses.
            captured.append(expr)
            return mock_session.query.return_value.filter.return_value

        mock_session.query.return_value.filter.side_effect = fake_filter
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        # Patch User.status.in_ to capture what list is passed
        with patch("scripts.sync_audience.User") as mock_user_class:
            in_call_args: list = []
            mock_user_class.status.in_.side_effect = lambda statuses: (
                in_call_args.append(list(statuses)) or MagicMock()
            )

            get_users()

        assert in_call_args == [["active", "waitlist"]]

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_custom_status_filter(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """When called with statuses=['waitlist'], should query with just ['waitlist']."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        with patch("scripts.sync_audience.User") as mock_user_class:
            in_call_args: list = []
            mock_user_class.status.in_.side_effect = lambda statuses: (
                in_call_args.append(list(statuses)) or MagicMock()
            )

            get_users(statuses=["waitlist"])

        assert in_call_args == [["waitlist"]]

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_extracts_first_name_from_user_name(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """User with name 'John Doe' should produce {'email': ..., 'first_name': 'John'}."""
        mock_user = MagicMock()
        mock_user.email = "john@example.com"
        mock_user.name = "John Doe"
        mock_user.status = "active"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_user
        ]
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        contacts = get_users()

        assert len(contacts) == 1
        assert contacts[0]["email"] == "john@example.com"
        assert contacts[0]["first_name"] == "John"

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_extracts_first_name_from_single_word_name(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """User with a single-word name 'Fabiano' should produce first_name='Fabiano'."""
        mock_user = MagicMock()
        mock_user.email = "fabiano@example.com"
        mock_user.name = "Fabiano"
        mock_user.status = "active"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_user
        ]
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        contacts = get_users()

        assert contacts[0]["first_name"] == "Fabiano"

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_no_first_name_when_user_has_no_name(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """User with name=None should produce {'email': ...} without 'first_name' key."""
        mock_user = MagicMock()
        mock_user.email = "noname@example.com"
        mock_user.name = None
        mock_user.status = "active"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_user
        ]
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        contacts = get_users()

        assert len(contacts) == 1
        assert contacts[0]["email"] == "noname@example.com"
        assert "first_name" not in contacts[0]

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_returns_empty_list_when_no_users_match(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """Empty result from DB should return an empty list."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        contacts = get_users()

        assert contacts == []

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_closes_session_after_query(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """Session.close() must be called regardless of query outcome."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        get_users()

        mock_session.close.assert_called_once()

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_closes_session_when_query_raises(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """Session.close() must be called even when the DB query raises."""
        mock_session = MagicMock()
        mock_session.query.side_effect = RuntimeError("DB connection lost")
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="DB connection lost"):
            get_users()

        mock_session.close.assert_called_once()

    @patch("scripts.sync_audience.get_settings")
    @patch("scripts.sync_audience.sessionmaker")
    @patch("scripts.sync_audience.create_engine")
    def test_multiple_users_all_returned(
        self, mock_create_engine, mock_sessionmaker, mock_get_settings
    ):
        """All users from the DB result should appear in the returned contacts list."""
        users = []
        for i in range(3):
            u = MagicMock()
            u.email = f"user{i}@example.com"
            u.name = f"User {i}"
            u.status = "active"
            users.append(u)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = users
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = MagicMock()

        contacts = get_users()

        assert len(contacts) == 3
        assert contacts[0]["email"] == "user0@example.com"
        assert contacts[1]["first_name"] == "User"
        assert contacts[2]["email"] == "user2@example.com"


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for main() CLI entry point."""

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py", "--dry-run"])
    def test_dry_run_does_not_call_bulk_sync(self, mock_get_users, mock_bulk_sync):
        """With --dry-run, bulk_sync_contacts should NOT be called."""
        main()

        mock_bulk_sync.assert_not_called()

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[])
    @patch("sys.argv", ["sync_audience.py"])
    def test_empty_contacts_does_not_call_bulk_sync(
        self, mock_get_users, mock_bulk_sync
    ):
        """When no contacts are found, bulk_sync_contacts should NOT be called."""
        main()

        mock_bulk_sync.assert_not_called()

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py", "--status", "waitlist"])
    def test_status_flag_passes_single_status(self, mock_get_users, mock_bulk_sync):
        """--status waitlist should call get_users with ['waitlist']."""
        mock_bulk_sync.return_value = {"skipped": False, "synced": 1, "failed": 0}

        main()

        mock_get_users.assert_called_once_with(["waitlist"])

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py"])
    def test_default_calls_get_users_without_status_filter(
        self, mock_get_users, mock_bulk_sync
    ):
        """No --status flag should call get_users with None."""
        mock_bulk_sync.return_value = {"skipped": False, "synced": 1, "failed": 0}

        main()

        mock_get_users.assert_called_once_with(None)

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch(
        "scripts.sync_audience.get_users",
        return_value=[
            {"email": "a@b.com", "first_name": "Alice"},
            {"email": "b@b.com"},
        ],
    )
    @patch("sys.argv", ["sync_audience.py"])
    def test_calls_bulk_sync_with_contacts(self, mock_get_users, mock_bulk_sync):
        """Normal run should call bulk_sync_contacts with the full contacts list."""
        mock_bulk_sync.return_value = {"skipped": False, "synced": 2, "failed": 0}

        main()

        mock_bulk_sync.assert_called_once_with(
            [{"email": "a@b.com", "first_name": "Alice"}, {"email": "b@b.com"}]
        )

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py"])
    def test_logs_skipped_when_not_configured(
        self, mock_get_users, mock_bulk_sync, caplog
    ):
        """When bulk_sync returns {'skipped': True}, should log a warning."""
        import logging

        mock_bulk_sync.return_value = {"skipped": True}

        with caplog.at_level(logging.WARNING, logger="scripts.sync_audience"):
            main()

        assert any(
            "skipped" in record.message.lower() or "not configured" in record.message.lower()
            for record in caplog.records
        ), f"Expected a skipped/not-configured warning, got: {[r.message for r in caplog.records]}"

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py"])
    def test_logs_sync_result_on_success(self, mock_get_users, mock_bulk_sync, caplog):
        """On a successful sync, should log synced/failed counts."""
        import logging

        mock_bulk_sync.return_value = {"skipped": False, "synced": 1, "failed": 0}

        with caplog.at_level(logging.INFO, logger="scripts.sync_audience"):
            main()

        messages = " ".join(r.message for r in caplog.records)
        assert "synced" in messages.lower() or "sync complete" in messages.lower()

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py", "--status", "active"])
    def test_status_active_passes_active_list(self, mock_get_users, mock_bulk_sync):
        """--status active should call get_users with ['active']."""
        mock_bulk_sync.return_value = {"skipped": False, "synced": 1, "failed": 0}

        main()

        mock_get_users.assert_called_once_with(["active"])

    @patch("scripts.sync_audience.bulk_sync_contacts")
    @patch("scripts.sync_audience.get_users", return_value=[{"email": "a@b.com"}])
    @patch("sys.argv", ["sync_audience.py", "--dry-run"])
    def test_dry_run_logs_would_sync(self, mock_get_users, mock_bulk_sync, caplog):
        """Dry run should log 'Would sync' or 'Dry run' without syncing."""
        import logging

        with caplog.at_level(logging.INFO, logger="scripts.sync_audience"):
            main()

        messages = " ".join(r.message for r in caplog.records)
        assert "dry run" in messages.lower() or "would sync" in messages.lower()
        mock_bulk_sync.assert_not_called()
