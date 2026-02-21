"""Tests for auth router — register, verify, and session-based /me."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_db
from apps.api.main import app
from packages.database.models.base import Base
from packages.database.models.session import SessionDB
from packages.database.models.user import User

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create test database session with fresh tables."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(db_session):
    """Create a registered user with a known password."""
    user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        name="Existing User",
        password_hash=bcrypt.hash("correct-password"),
        auth_provider="email",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def active_session(db_session, registered_user):
    """Create a valid, non-expired session for the registered user."""
    session = SessionDB(
        id=uuid.uuid4(),
        session_token="valid-session-token-abc",
        user_id=registered_user.id,
        expires=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def expired_session(db_session, registered_user):
    """Create an expired session for the registered user."""
    session = SessionDB(
        id=uuid.uuid4(),
        session_token="expired-session-token-xyz",
        user_id=registered_user.id,
        expires=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(session)
    db_session.commit()
    return session


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    """Tests for POST /api/auth/register."""

    def test_register_success(self, client):
        """Registering with valid email and password creates a user."""
        payload = {
            "email": "new@example.com",
            "password": "strong-password-123",
            "name": "New User",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["name"] == "New User"
        assert data["status"] == "active"
        assert "id" in data
        # Password hash must NOT leak into the response
        assert "password_hash" not in data
        assert "password" not in data

    def test_register_normalizes_email(self, client):
        """Email is lowercased and trimmed before storage."""
        payload = {
            "email": "  Test@Example.COM  ",
            "password": "strong-password-123",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        assert response.json()["email"] == "test@example.com"

    def test_register_duplicate_email(self, client, registered_user):
        """Registering with an already-taken email returns 409."""
        payload = {
            "email": "existing@example.com",
            "password": "another-password-456",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Registering with a malformed email returns 400."""
        payload = {
            "email": "not-an-email",
            "password": "strong-password-123",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 400
        assert "invalido" in response.json()["detail"].lower()

    def test_register_missing_email(self, client):
        """Omitting the email field returns 422 (validation error)."""
        payload = {"password": "strong-password-123"}
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """Omitting the password field returns 422 (validation error)."""
        payload = {"email": "test@example.com"}
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """A password shorter than 8 characters returns 422."""
        payload = {
            "email": "test@example.com",
            "password": "short",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 422

    def test_register_name_optional(self, client):
        """Registering without a name succeeds (name is optional)."""
        payload = {
            "email": "noname@example.com",
            "password": "strong-password-123",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        assert response.json()["name"] is None

    def test_register_password_is_hashed(self, client, db_session):
        """The stored password_hash is a bcrypt hash, not plaintext."""
        payload = {
            "email": "hash-check@example.com",
            "password": "my-secret-password",
        }
        client.post("/api/auth/register", json=payload)

        user = (
            db_session.query(User)
            .filter(User.email == "hash-check@example.com")
            .first()
        )
        assert user is not None
        assert user.password_hash != "my-secret-password"
        assert bcrypt.verify("my-secret-password", user.password_hash)

    def test_register_triggers_welcome_email(self, client, monkeypatch):
        """Registration queues a welcome email via BackgroundTasks.

        FastAPI TestClient runs BackgroundTasks synchronously, so the
        send_welcome_email function will be called before the response
        is returned.
        """
        import apps.api.routers.auth as auth_module

        calls = []

        def fake_send_welcome_email(email: str, name=None):
            calls.append({"email": email, "name": name})
            return True

        monkeypatch.setattr(auth_module, "send_welcome_email", fake_send_welcome_email)

        payload = {
            "email": "welcome-test@example.com",
            "password": "strong-password-123",
            "name": "Welcome User",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        assert len(calls) == 1
        assert calls[0]["email"] == "welcome-test@example.com"
        assert calls[0]["name"] == "Welcome User"

    def test_register_triggers_welcome_email_without_name(self, client, monkeypatch):
        """Welcome email is triggered even when name is not provided."""
        import apps.api.routers.auth as auth_module

        calls = []

        def fake_send_welcome_email(email: str, name=None):
            calls.append({"email": email, "name": name})
            return True

        monkeypatch.setattr(auth_module, "send_welcome_email", fake_send_welcome_email)

        payload = {
            "email": "noname-welcome@example.com",
            "password": "strong-password-123",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        assert len(calls) == 1
        assert calls[0]["email"] == "noname-welcome@example.com"
        assert calls[0]["name"] is None

    def test_register_upgrades_waitlist_user(self, client, db_session):
        """A waitlist user (no password) is upgraded to active on register."""
        waitlist_user = User(
            id=uuid.uuid4(),
            email="waitlist@example.com",
            name="Waitlist User",
            password_hash=None,
            auth_provider="email",
            status="waitlist",
            waitlist_position=42,
        )
        db_session.add(waitlist_user)
        db_session.commit()
        original_id = str(waitlist_user.id)

        payload = {
            "email": "waitlist@example.com",
            "password": "new-password-123",
            "name": "Upgraded User",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["id"] == original_id  # Same user, not a new one
        assert data["name"] == "Upgraded User"

    def test_register_upgrade_preserves_waitlist_position(self, client, db_session):
        """Upgrading a waitlist user preserves their waitlist_position."""
        waitlist_user = User(
            id=uuid.uuid4(),
            email="keeper@example.com",
            password_hash=None,
            status="waitlist",
            waitlist_position=7,
        )
        db_session.add(waitlist_user)
        db_session.commit()

        payload = {
            "email": "keeper@example.com",
            "password": "new-password-123",
        }
        client.post("/api/auth/register", json=payload)

        db_session.refresh(waitlist_user)
        assert waitlist_user.status == "active"
        assert waitlist_user.waitlist_position == 7

    def test_register_rejects_active_duplicate(self, client, registered_user):
        """An active user with password cannot be 're-registered'."""
        payload = {
            "email": "existing@example.com",
            "password": "another-password-456",
        }
        response = client.post("/api/auth/register", json=payload)

        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/auth/verify
# ---------------------------------------------------------------------------


class TestVerify:
    """Tests for POST /api/auth/verify."""

    def test_verify_valid_credentials(self, client, registered_user):
        """Valid email + password returns the user profile."""
        payload = {
            "email": "existing@example.com",
            "password": "correct-password",
        }
        response = client.post("/api/auth/verify", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "existing@example.com"
        assert data["name"] == "Existing User"
        assert "password_hash" not in data

    def test_verify_invalid_password(self, client, registered_user):
        """Wrong password returns 401."""
        payload = {
            "email": "existing@example.com",
            "password": "wrong-password",
        }
        response = client.post("/api/auth/verify", json=payload)

        assert response.status_code == 401
        assert "invalidas" in response.json()["detail"].lower()

    def test_verify_nonexistent_user(self, client):
        """Email that does not exist returns 401."""
        payload = {
            "email": "ghost@example.com",
            "password": "some-password",
        }
        response = client.post("/api/auth/verify", json=payload)

        assert response.status_code == 401
        assert "invalidas" in response.json()["detail"].lower()

    def test_verify_user_without_password(self, client, db_session):
        """A user registered via OAuth (no password_hash) returns 401."""
        oauth_user = User(
            id=uuid.uuid4(),
            email="oauth@example.com",
            name="OAuth User",
            password_hash=None,
            auth_provider="google",
            status="active",
        )
        db_session.add(oauth_user)
        db_session.commit()

        payload = {
            "email": "oauth@example.com",
            "password": "any-password",
        }
        response = client.post("/api/auth/verify", json=payload)

        assert response.status_code == 401

    def test_verify_updates_last_login(self, client, db_session, registered_user):
        """Successful verification updates last_login_at."""
        assert registered_user.last_login_at is None

        payload = {
            "email": "existing@example.com",
            "password": "correct-password",
        }
        client.post("/api/auth/verify", json=payload)

        db_session.refresh(registered_user)
        assert registered_user.last_login_at is not None


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    """Tests for GET /api/auth/me."""

    def test_me_with_valid_session(self, client, active_session, registered_user):
        """A valid session token returns the user profile."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid-session-token-abc"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "existing@example.com"
        assert data["name"] == "Existing User"
        assert "password_hash" not in data

    def test_me_without_token(self, client):
        """Missing Authorization header returns 401."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "ausente" in response.json()["detail"].lower()

    def test_me_with_invalid_token(self, client):
        """A token that does not match any session returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer non-existent-token"},
        )

        assert response.status_code == 401
        assert "invalida" in response.json()["detail"].lower()

    def test_me_with_expired_session(self, client, expired_session):
        """An expired session token returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer expired-session-token-xyz"},
        )

        assert response.status_code == 401
        assert "expirada" in response.json()["detail"].lower()

    def test_me_with_bad_auth_format(self, client):
        """A malformed Authorization header returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Basic some-token"},
        )

        assert response.status_code == 401
        assert "invalido" in response.json()["detail"].lower()

    def test_me_with_token_only_no_bearer(self, client):
        """Authorization header without 'Bearer' prefix returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "just-a-token"},
        )

        assert response.status_code == 401
