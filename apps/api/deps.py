"""Dependency injection for the API layer.

Provides database sessions, configuration, and admin auth to route handlers.
"""

from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import get_settings
from packages.database.models.session import SessionDB
from packages.database.models.user import User

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


def get_admin_user(
    authorization: str = Header(None),
    x_admin_email: str = Header(None),
    x_admin_secret: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that authenticates an admin user.

    Supports two auth methods:
    1. Service-to-service: X-Admin-Email + X-Admin-Secret headers
       (used by the Next.js API route proxy)
    2. Bearer session token: Authorization: Bearer <session_token>
       (used by direct API calls with database sessions)

    Both methods verify the user's email is in the ADMIN_EMAILS allowlist.
    Returns the User or raises 401/403.
    """
    settings = get_settings()

    # --- Method 1: Service-to-service auth (Next.js proxy) ---
    if x_admin_email and x_admin_secret:
        if not settings.admin_api_secret:
            raise HTTPException(status_code=500, detail="ADMIN_API_SECRET nao configurado.")
        if x_admin_secret != settings.admin_api_secret:
            raise HTTPException(status_code=401, detail="Secret de admin invalido.")

        email = x_admin_email.strip().lower()
        if email not in settings.admin_emails_list:
            raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
        return user

    # --- Method 2: Bearer session token ---
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de sessao ausente.")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Formato de autorizacao invalido.")

    token = parts[1]

    session = db.query(SessionDB).filter(SessionDB.session_token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Sessao invalida.")

    now_utc = datetime.now(timezone.utc)
    expires = session.expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now_utc:
        raise HTTPException(status_code=401, detail="Sessao expirada.")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")

    if user.email.lower() not in settings.admin_emails_list:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")

    return user
