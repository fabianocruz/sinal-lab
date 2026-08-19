"""Tests for API rate limiting (slowapi).

The limiter ships disabled under API_ENV=test (conftest sets it before
app import) so the rest of the suite is unaffected; these tests enable
it explicitly to exercise the 429 path and reset counters afterwards.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_db
from apps.api.main import app
from apps.api.ratelimit import limiter
from packages.database.models import Base

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def enabled_limiter():
    """Enable rate limiting for one test; reset counters on teardown."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False


class TestRateLimitConfig:
    def test_limiter_disabled_under_test_env(self):
        """conftest sets API_ENV=test, which must disable the limiter
        so the rest of the suite never trips it."""
        assert limiter.enabled is False

    def test_suite_traffic_not_limited_when_disabled(self, client):
        """With the limiter disabled, burst traffic sails through."""
        for i in range(15):
            resp = client.post(
                "/api/waitlist", json={"email": f"burst{i}@example.com"}
            )
            assert resp.status_code != 429


class TestSignupRateLimit:
    def test_waitlist_signup_429_beyond_limit(self, client, enabled_limiter):
        """The 11th signup from one IP inside a minute is rejected
        (rate_limit_signup default: 10/minute)."""
        statuses = [
            client.post(
                "/api/waitlist", json={"email": f"rl{i}@example.com"}
            ).status_code
            for i in range(11)
        ]
        assert 429 not in statuses[:10]
        assert statuses[10] == 429

    def test_429_uses_project_error_format(self, client, enabled_limiter):
        for i in range(11):
            resp = client.post(
                "/api/waitlist", json={"email": f"fmt{i}@example.com"}
            )
        body = resp.json()
        assert body["code"] == "RATE_LIMITED"
        assert "Rate limit exceeded" in body["detail"]

    def test_register_429_beyond_limit(self, client, enabled_limiter):
        statuses = [
            client.post(
                "/api/auth/register",
                json={
                    "email": f"reg{i}@example.com",
                    "password": "strong-pass-123",
                },
            ).status_code
            for i in range(11)
        ]
        assert statuses[10] == 429

    def test_health_stays_exempt_while_signup_is_limited(
        self, client, enabled_limiter
    ):
        """Hitting the signup limit must not affect /health (exempt)."""
        for i in range(11):
            client.post("/api/waitlist", json={"email": f"hx{i}@example.com"})
        assert client.get("/health").status_code == 200
