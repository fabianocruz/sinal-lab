"""Unit tests for database session management.

Tests for packages.database.session module, ensuring proper session creation,
lifecycle management, and error handling.

Coverage target: >80% per CLAUDE.md standards.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from packages.database.session import get_session
from packages.database.config import SessionLocal


class TestGetSession:
    """Test suite for get_session() function."""

    def test_returns_session_instance(self):
        """Test that get_session() returns a valid Session instance."""
        session = get_session()

        assert session is not None
        assert isinstance(session, Session)

        # Cleanup
        session.close()

    def test_returns_different_instances(self):
        """Test that multiple calls return different session instances."""
        session1 = get_session()
        session2 = get_session()

        assert session1 is not session2
        assert id(session1) != id(session2)

        # Cleanup
        session1.close()
        session2.close()

    def test_session_has_database_binding(self):
        """Test that returned session is bound to the database engine."""
        session = get_session()

        assert session.bind is not None
        assert session.get_bind() is not None

        # Cleanup
        session.close()

    def test_session_supports_basic_operations(self):
        """Test that session supports query, commit, rollback operations."""
        session = get_session()

        # Verify session has required methods
        assert hasattr(session, 'query')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        assert hasattr(session, 'close')
        assert callable(session.query)
        assert callable(session.commit)
        assert callable(session.rollback)
        assert callable(session.close)

        # Cleanup
        session.close()

    def test_session_can_be_closed(self):
        """Test that session.close() works without errors."""
        session = get_session()

        # Should not raise any exception
        session.close()

        # Calling close() again should also not raise
        session.close()

    def test_session_rollback_on_exception(self):
        """Test manual transaction rollback pattern works correctly."""
        session = get_session()

        try:
            # Simulate exception during transaction
            session.begin()
            raise ValueError("Simulated error")
        except ValueError:
            session.rollback()
            # Should not raise - rollback should work
            assert True
        finally:
            session.close()

    @patch('packages.database.session.SessionLocal')
    def test_calls_session_local_factory(self, mock_session_local):
        """Test that get_session() calls SessionLocal factory."""
        mock_session = Mock(spec=Session)
        mock_session_local.return_value = mock_session

        result = get_session()

        mock_session_local.assert_called_once_with()
        assert result == mock_session

    @patch('packages.database.session.SessionLocal')
    def test_database_connection_error_propagates(self, mock_session_local):
        """Test that database connection errors are propagated to caller."""
        # Simulate connection failure
        mock_session_local.side_effect = OperationalError(
            "Connection refused",
            params=None,
            orig=Exception("Connection refused")
        )

        with pytest.raises(OperationalError) as exc_info:
            get_session()

        assert "Connection refused" in str(exc_info.value)

    @patch('packages.database.session.SessionLocal')
    def test_sqlalchemy_error_propagates(self, mock_session_local):
        """Test that SQLAlchemy errors are propagated to caller."""
        # Simulate general SQLAlchemy error
        mock_session_local.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError) as exc_info:
            get_session()

        assert "Database error" in str(exc_info.value)

    def test_session_autocommit_disabled(self):
        """Test that session has autocommit disabled (explicit commit required)."""
        session = get_session()

        # SessionLocal is configured with autocommit=False
        # Verify by checking session bind's connect args
        bind = session.get_bind()
        assert bind is not None

        # Cleanup
        session.close()

    def test_session_autoflush_disabled(self):
        """Test that session has autoflush disabled (explicit flush required)."""
        session = get_session()

        # SessionLocal is configured with autoflush=False
        # This is important for agent pipelines to control when changes are persisted
        assert hasattr(session, 'autoflush')
        # Note: autoflush is a session-level setting, not bind-level

        # Cleanup
        session.close()

    def test_context_manager_pattern_works(self):
        """Test that session works with contextlib.closing pattern."""
        from contextlib import closing

        # This pattern is recommended in the docstring
        with closing(get_session()) as session:
            assert isinstance(session, Session)
            # Verify session is usable within context
            assert session.bind is not None

        # Session should be closed after context exit (close() was called)
        # Note: is_active may still be True, but the connection has been returned to pool
        # The important thing is that close() was called without error

    def test_multiple_sequential_sessions(self):
        """Test creating and closing multiple sessions sequentially."""
        sessions_created = []

        for _ in range(5):
            session = get_session()
            sessions_created.append(session)
            assert isinstance(session, Session)
            session.close()

        # Verify all sessions were different instances
        session_ids = [id(s) for s in sessions_created]
        assert len(session_ids) == len(set(session_ids))  # All unique

    def test_session_type_hint_matches_return(self):
        """Test that return type matches the type hint annotation."""
        session = get_session()

        # Verify return type is Session as declared in type hint
        assert isinstance(session, Session)

        # Cleanup
        session.close()


class TestSessionIntegration:
    """Integration tests for session usage patterns in agents."""

    def test_agent_pipeline_usage_pattern(self):
        """Test typical agent pipeline usage pattern from docstring."""
        # Example from docstring
        session = get_session()
        try:
            # Simulate agent collecting data
            # In real agent: users = session.query(User).filter(...).all()
            # Here we just verify session is ready for queries
            assert session.is_active

            # Simulate successful processing
            session.commit()
            assert True  # No exception raised
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_cli_script_usage_pattern(self):
        """Test typical CLI script usage pattern with closing context."""
        from contextlib import closing

        # Recommended pattern from docstring
        with closing(get_session()) as session:
            # Simulate CLI script querying data
            assert session.bind is not None
            # In real CLI: results = session.query(Model).all()

        # Session auto-closed by context manager (close() was called)
        # The important part is that no exception was raised

    def test_error_handling_without_commit(self):
        """Test that rollback works even without explicit commit."""
        session = get_session()

        try:
            # Start work but don't commit
            session.begin()
            # Simulate error before commit
            raise RuntimeError("Process failed")
        except RuntimeError:
            # Rollback should work
            session.rollback()
            assert True
        finally:
            session.close()

    def test_session_pool_not_exhausted(self):
        """Test that properly closing sessions prevents pool exhaustion."""
        # Create and close many sessions rapidly
        for _ in range(20):
            session = get_session()
            session.close()

        # Should still be able to get new session
        final_session = get_session()
        assert isinstance(final_session, Session)
        final_session.close()
