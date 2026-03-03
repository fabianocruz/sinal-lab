"""Tests for cover image generation endpoint.

The endpoint delegates to CoverPipeline which is mocked in tests.
Auth follows the same pattern as test_admin_content.py.

Run: pytest apps/api/tests/test_covers.py -v
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_admin_user, get_db
from apps.api.main import app
from packages.database.models.base import Base
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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="admin@sinal.tech",
        name="Admin User",
        auth_provider="email",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def client(db_session, admin_user):
    """Test client with admin auth override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_admin_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_admin_user] = override_get_admin_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(db_session):
    """Test client without admin auth."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


VALID_BODY = {
    "headline": "Nubank testa agentes de AI",
    "lede": "O maior banco digital da LATAM iniciou testes",
    "agent": "radar",
    "edition": 30,
    "dq_score": 4.0,
    "variations": 2,
}


def _mock_pipeline_success(mock_cls):
    """Configure mock CoverPipeline to return 2 successful images."""
    from apps.agents.covers.pipeline import CoverResult

    instance = mock_cls.return_value
    instance.run.return_value = CoverResult(
        images=[
            {"url": "https://blob.vercel-storage.com/covers/radar/ed30-v1.png", "variation": 1, "pathname": "covers/radar/ed30-v1.png"},
            {"url": "https://blob.vercel-storage.com/covers/radar/ed30-v2.png", "variation": 2, "pathname": "covers/radar/ed30-v2.png"},
        ],
        prompt_used="Dark editorial illustration.",
        agent="radar",
        errors=[],
    )


def _mock_pipeline_failure(mock_cls):
    """Configure mock CoverPipeline to return failure."""
    from apps.agents.covers.pipeline import CoverResult

    instance = mock_cls.return_value
    instance.run.return_value = CoverResult(
        images=[],
        prompt_used="",
        agent="radar",
        errors=["Prompt generation failed"],
    )


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_success(mock_pipeline_cls, client):
    _mock_pipeline_success(mock_pipeline_cls)

    response = client.post("/api/covers/generate", json=VALID_BODY)

    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) == 2
    assert data["images"][0]["variation"] == 1
    assert "blob.vercel-storage.com" in data["images"][0]["url"]
    assert data["prompt_used"] == "Dark editorial illustration."
    assert data["agent"] == "radar"
    assert data["errors"] == []


def test_generate_cover_requires_admin(unauth_client):
    response = unauth_client.post("/api/covers/generate", json=VALID_BODY)
    assert response.status_code in (401, 403)


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_invalid_agent(mock_pipeline_cls, client):
    body = {**VALID_BODY, "agent": "unknown"}
    response = client.post("/api/covers/generate", json=body)
    assert response.status_code == 422


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_missing_headline(mock_pipeline_cls, client):
    body = {**VALID_BODY}
    del body["headline"]
    response = client.post("/api/covers/generate", json=body)
    assert response.status_code == 422


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_missing_lede(mock_pipeline_cls, client):
    body = {**VALID_BODY}
    del body["lede"]
    response = client.post("/api/covers/generate", json=body)
    assert response.status_code == 422


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_pipeline_failure(mock_pipeline_cls, client):
    _mock_pipeline_failure(mock_pipeline_cls)

    response = client.post("/api/covers/generate", json=VALID_BODY)

    assert response.status_code == 502
    assert "Prompt generation failed" in response.json()["detail"]


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_partial_success(mock_pipeline_cls, client):
    from apps.agents.covers.pipeline import CoverResult

    instance = mock_pipeline_cls.return_value
    instance.run.return_value = CoverResult(
        images=[{"url": "https://blob.vercel-storage.com/v1.png", "variation": 1, "pathname": "v1.png"}],
        prompt_used="A prompt.",
        agent="radar",
        errors=["Upload failed for variation 2"],
    )

    response = client.post("/api/covers/generate", json=VALID_BODY)

    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) == 1
    assert len(data["errors"]) == 1


@patch("apps.api.routers.covers.CoverPipeline")
def test_generate_cover_default_variations(mock_pipeline_cls, client):
    _mock_pipeline_success(mock_pipeline_cls)

    body = {**VALID_BODY}
    del body["variations"]
    response = client.post("/api/covers/generate", json=body)

    assert response.status_code == 200
    # Verify pipeline was called with default variations=3
    instance = mock_pipeline_cls.return_value
    call_args = instance.run.call_args
    assert call_args.kwargs.get("variations", call_args.args[1] if len(call_args.args) > 1 else 3) == 3
