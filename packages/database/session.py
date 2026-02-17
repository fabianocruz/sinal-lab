"""Database session management for agents and CLI scripts.

This module provides session factory functions for direct database access
outside of FastAPI's dependency injection context. Used primarily by AI agents
and command-line tools that need to interact with the database.

Typical usage:
    from packages.database.session import get_session

    session = get_session()
    try:
        users = session.query(User).filter(User.status == "active").all()
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
"""

from typing import ContextManager

from sqlalchemy.orm import Session

from packages.database.config import SessionLocal


def get_session() -> Session:
    """Get a new database session for direct use (non-FastAPI context).

    Returns a SQLAlchemy Session instance that must be manually managed by the caller.
    The session is not automatically committed or rolled back - the caller is responsible
    for transaction management and cleanup.

    This function is primarily used in:
    - AI agent pipelines (SINTESE, RADAR, FUNDING, MERCADO, CODIGO)
    - CLI scripts and data migration tools
    - Background jobs and scheduled tasks

    Returns:
        Session: A new SQLAlchemy session bound to the configured database engine.
            The session must be explicitly closed by the caller when done.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If database connection fails or configuration
            is invalid.

    Example:
        Basic usage with manual cleanup:
        >>> session = get_session()
        >>> try:
        ...     users = session.query(User).all()
        ...     session.commit()
        ... except Exception:
        ...     session.rollback()
        ...     raise
        ... finally:
        ...     session.close()

        Safer usage with context manager:
        >>> from contextlib import closing
        >>> with closing(get_session()) as session:
        ...     users = session.query(User).all()

    See Also:
        - packages.database.config.get_db: FastAPI dependency injection version
        - packages.database.config.SessionLocal: The underlying session factory

    Warning:
        Always close the session to avoid connection pool exhaustion.
        Prefer using context managers (with closing(...)) for automatic cleanup.
    """
    return SessionLocal()
