"""Dependency injection for the API layer.

Provides database sessions and configuration to route handlers.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    """Create (or reuse) a SQLAlchemy engine from settings."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    """Create (or reuse) a session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session.

    Yields a session and ensures it's closed after the request.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
