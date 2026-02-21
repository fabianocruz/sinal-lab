"""Auth router — registration, credential verification, and session lookup."""

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.auth import RegisterRequest, UserResponse, VerifyRequest
from apps.api.services.email import send_welcome_email
from packages.database.models.session import SessionDB
from packages.database.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new account with email and password.

    The password is hashed with bcrypt before storage. The user
    starts with status='active' and auth_provider='email'.
    """
    email = body.email.strip().lower()

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Email invalido.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        # Upgrade waitlist-only users (no password) to active members
        if existing.status == "waitlist" and not existing.password_hash:
            existing.password_hash = bcrypt.hash(body.password)
            existing.name = body.name or existing.name
            existing.status = "active"
            existing.auth_provider = "email"
            db.commit()
            db.refresh(existing)
            background_tasks.add_task(send_welcome_email, existing.email, existing.name)
            return UserResponse.model_validate(existing)
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    user = User(
        id=uuid.uuid4(),
        email=email,
        name=body.name,
        password_hash=bcrypt.hash(body.password),
        auth_provider="email",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_welcome_email, user.email, body.name)

    return UserResponse.model_validate(user)


@router.post("/verify", response_model=UserResponse)
def verify_credentials(body: VerifyRequest, db: Session = Depends(get_db)):
    """Verify email/password credentials.

    Called by NextAuth's CredentialsProvider to authenticate a user.
    Returns the user profile on success, 401 on invalid credentials.
    Also updates the user's last_login_at timestamp.
    """
    email = body.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais invalidas.")

    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Credenciais invalidas.")

    if not bcrypt.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais invalidas.")

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Get the current authenticated user via session token.

    Expects an Authorization header with format: Bearer <session_token>.
    Looks up the session, validates it has not expired, and returns
    the associated user profile.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de sessao ausente.")

    # Parse "Bearer <token>" format
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Formato de authorization invalido.")

    token = parts[1]

    session = (
        db.query(SessionDB).filter(SessionDB.session_token == token).first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Sessao invalida.")

    # Compare expiration: normalize to UTC. SQLite returns naive datetimes,
    # PostgreSQL returns timezone-aware ones.
    now_utc = datetime.now(timezone.utc)
    expires = session.expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now_utc:
        raise HTTPException(status_code=401, detail="Sessao expirada.")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")

    return UserResponse.model_validate(user)
