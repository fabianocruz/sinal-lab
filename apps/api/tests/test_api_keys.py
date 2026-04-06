"""Tests for API key authentication system.

Covers:
- Admin endpoint to create API keys (POST /api/admin/api-keys)
- Admin endpoint to list API keys (GET /api/admin/api-keys)
- Admin endpoint to revoke API keys (DELETE /api/admin/api-keys/{id})
- get_api_key dependency (valid, invalid, inactive, expired keys)
- optional_api_key dependency (no header returns None)

Uses SQLite in-memory with StaticPool so all threads share the same
database connection.

Run: pytest apps/api/tests/test_api_keys.py -v
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_api_key, get_db, optional_api_key
from apps.api.main import app
from packages.database.models.api_key import ApiKey
from packages.database.models.base import Base

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ADMIN_SECRET = "test-admin-secret-12345"


@pytest.fixture(autouse=True)
def _set_admin_secret(monkeypatch):
    """Ensure ADMIN_API_SECRET is set for all tests."""
    monkeypatch.setenv("ADMIN_API_SECRET", ADMIN_SECRET)
    # Clear the cached settings so the monkeypatched env var is picked up
    from apps.api.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_session():
    """Create test database session."""
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


def admin_headers() -> dict:
    """Return headers with the admin secret."""
    return {"Authorization": f"Bearer {ADMIN_SECRET}"}


# ---------------------------------------------------------------------------
# Admin endpoint: create API key
# ---------------------------------------------------------------------------


class TestCreateApiKey:
    """Tests for POST /api/admin/api-keys."""

    def test_create_api_key_success(self, client, db_session):
        """Creating an API key returns the plaintext key and stores the hash."""
        resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "My App"},
            headers=admin_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["api_key"].startswith("sk_live_")
        assert data["name"] == "My App"
        assert data["key_prefix"] == data["api_key"][:12]

        # Verify the hash is stored in DB
        expected_hash = hashlib.sha256(data["api_key"].encode()).hexdigest()
        db_key = db_session.query(ApiKey).filter(ApiKey.key_hash == expected_hash).first()
        assert db_key is not None
        assert db_key.user_email == "dev@startup.com"
        assert db_key.is_active is True
        assert db_key.rate_limit == 100

    def test_create_api_key_without_admin_secret_returns_401(self, client):
        """Missing admin secret returns 401."""
        resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "My App"},
        )
        assert resp.status_code == 401

    def test_create_api_key_wrong_admin_secret_returns_401(self, client):
        """Wrong admin secret returns 401."""
        resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "My App"},
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert resp.status_code == 401

    def test_create_api_key_invalid_email_returns_422(self, client):
        """Invalid email format returns 422 (Pydantic validation)."""
        resp = client.post(
            "/api/admin/api-keys",
            json={"email": "not-an-email", "name": "My App"},
            headers=admin_headers(),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Admin endpoint: list API keys
# ---------------------------------------------------------------------------


class TestListApiKeys:
    """Tests for GET /api/admin/api-keys."""

    def test_list_api_keys_empty(self, client):
        """Returns empty list when no keys exist."""
        resp = client.get("/api/admin/api-keys", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_api_keys_returns_metadata(self, client):
        """Created keys appear in the list without plaintext key."""
        # Create two keys
        client.post(
            "/api/admin/api-keys",
            json={"email": "a@example.com", "name": "Key A"},
            headers=admin_headers(),
        )
        client.post(
            "/api/admin/api-keys",
            json={"email": "b@example.com", "name": "Key B"},
            headers=admin_headers(),
        )

        resp = client.get("/api/admin/api-keys", headers=admin_headers())
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) == 2

        # No plaintext key in list response
        for key in keys:
            assert "api_key" not in key
            assert key["key_prefix"].startswith("sk_live_")

    def test_list_api_keys_filter_by_email(self, client):
        """Filtering by email returns only matching keys."""
        client.post(
            "/api/admin/api-keys",
            json={"email": "a@example.com", "name": "Key A"},
            headers=admin_headers(),
        )
        client.post(
            "/api/admin/api-keys",
            json={"email": "b@example.com", "name": "Key B"},
            headers=admin_headers(),
        )

        resp = client.get(
            "/api/admin/api-keys?email=a@example.com",
            headers=admin_headers(),
        )
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) == 1
        assert keys[0]["user_email"] == "a@example.com"

    def test_list_api_keys_requires_admin(self, client):
        """Listing keys without admin secret returns 401."""
        resp = client.get("/api/admin/api-keys")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin endpoint: revoke API key
# ---------------------------------------------------------------------------


class TestRevokeApiKey:
    """Tests for DELETE /api/admin/api-keys/{key_id}."""

    def test_revoke_api_key_success(self, client, db_session):
        """Revoking a key sets is_active to False."""
        # Create a key
        create_resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "Revoke Me"},
            headers=admin_headers(),
        )
        raw_key = create_resp.json()["api_key"]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db_key = db_session.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

        # Revoke
        resp = client.delete(
            f"/api/admin/api-keys/{db_key.id}",
            headers=admin_headers(),
        )
        assert resp.status_code == 204

        # Verify it's inactive
        db_session.refresh(db_key)
        assert db_key.is_active is False

    def test_revoke_nonexistent_key_returns_404(self, client):
        """Revoking a key that doesn't exist returns 404."""
        resp = client.delete(
            f"/api/admin/api-keys/{uuid.uuid4()}",
            headers=admin_headers(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# get_api_key dependency
# ---------------------------------------------------------------------------


class TestGetApiKeyDependency:
    """Tests for the get_api_key FastAPI dependency."""

    def _create_key(self, client) -> str:
        """Helper: create a key and return the raw plaintext."""
        resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "Test Key"},
            headers=admin_headers(),
        )
        return resp.json()["api_key"]

    def test_valid_key_authenticates(self, client):
        """A valid API key passes the get_api_key dependency."""
        raw_key = self._create_key(client)

        # Add a temporary test endpoint that requires get_api_key
        @app.get("/test/protected")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"email": api_key.user_email, "name": api_key.name}

        try:
            resp = client.get(
                "/test/protected",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["email"] == "dev@startup.com"
            assert data["name"] == "Test Key"
        finally:
            # Clean up the test route
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected"]

    def test_missing_header_returns_401(self, client):
        """No Authorization header returns 401."""

        @app.get("/test/protected-missing")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            resp = client.get("/test/protected-missing")
            assert resp.status_code == 401
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-missing"]

    def test_invalid_key_returns_401(self, client):
        """A non-existent key returns 401."""

        @app.get("/test/protected-invalid")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            resp = client.get(
                "/test/protected-invalid",
                headers={"Authorization": "Bearer sk_live_doesnotexist"},
            )
            assert resp.status_code == 401
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-invalid"]

    def test_inactive_key_returns_403(self, client, db_session):
        """An inactive key returns 403."""
        raw_key = self._create_key(client)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db_key = db_session.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        db_key.is_active = False
        db_session.commit()

        @app.get("/test/protected-inactive")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            resp = client.get(
                "/test/protected-inactive",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 403
            assert "desativada" in resp.json()["detail"]
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-inactive"]

    def test_expired_key_returns_403(self, client, db_session):
        """An expired key returns 403."""
        raw_key = self._create_key(client)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db_key = db_session.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        db_key.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        @app.get("/test/protected-expired")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            resp = client.get(
                "/test/protected-expired",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 403
            assert "expirada" in resp.json()["detail"]
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-expired"]

    def test_valid_key_updates_last_used_at(self, client, db_session):
        """Authenticating with a valid key updates last_used_at."""
        raw_key = self._create_key(client)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db_key = db_session.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        assert db_key.last_used_at is None

        @app.get("/test/protected-timestamp")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            client.get(
                "/test/protected-timestamp",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            db_session.refresh(db_key)
            assert db_key.last_used_at is not None
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-timestamp"]

    def test_malformed_authorization_header_returns_401(self, client):
        """Malformed Authorization header (not Bearer) returns 401."""

        @app.get("/test/protected-malformed")
        def protected_endpoint(api_key: ApiKey = Depends(get_api_key)):
            return {"ok": True}

        try:
            resp = client.get(
                "/test/protected-malformed",
                headers={"Authorization": "Basic abc123"},
            )
            assert resp.status_code == 401
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/protected-malformed"]


# ---------------------------------------------------------------------------
# optional_api_key dependency
# ---------------------------------------------------------------------------


class TestOptionalApiKeyDependency:
    """Tests for the optional_api_key dependency."""

    def test_no_header_returns_none(self, client):
        """No Authorization header returns None (not 401)."""

        @app.get("/test/optional-none")
        def optional_endpoint(api_key=Depends(optional_api_key)):
            return {"authenticated": api_key is not None}

        try:
            resp = client.get("/test/optional-none")
            assert resp.status_code == 200
            assert resp.json()["authenticated"] is False
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/optional-none"]

    def test_valid_header_returns_key(self, client):
        """Valid Authorization header returns the ApiKey."""
        # Create a key
        create_resp = client.post(
            "/api/admin/api-keys",
            json={"email": "dev@startup.com", "name": "Optional Test"},
            headers=admin_headers(),
        )
        raw_key = create_resp.json()["api_key"]

        @app.get("/test/optional-valid")
        def optional_endpoint(api_key=Depends(optional_api_key)):
            return {"authenticated": api_key is not None, "email": api_key.user_email if api_key else None}

        try:
            resp = client.get(
                "/test/optional-valid",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["authenticated"] is True
            assert data["email"] == "dev@startup.com"
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/optional-valid"]

    def test_invalid_header_still_returns_401(self, client):
        """Invalid key with optional dependency still returns 401."""

        @app.get("/test/optional-invalid")
        def optional_endpoint(api_key=Depends(optional_api_key)):
            return {"ok": True}

        try:
            resp = client.get(
                "/test/optional-invalid",
                headers={"Authorization": "Bearer sk_live_bogus"},
            )
            assert resp.status_code == 401
        finally:
            app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test/optional-invalid"]
