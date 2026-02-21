"""Tests for admin content router — CRUD, auth, publish lifecycle.

Uses SQLite in-memory with StaticPool (same pattern as other API tests).

Run: pytest apps/api/tests/test_admin_content.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_admin_user, get_db
from apps.api.main import app
from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece
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
def admin_user(db_session):
    """Create an admin user."""
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
def non_admin_user(db_session):
    """Create a non-admin user with a valid session."""
    user = User(
        id=uuid.uuid4(),
        email="regular@example.com",
        name="Regular User",
        auth_provider="email",
        status="active",
    )
    db_session.add(user)
    db_session.commit()

    session = SessionDB(
        id=uuid.uuid4(),
        session_token="non-admin-token",
        user_id=user.id,
        expires=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()
    return user


@pytest.fixture
def client(db_session, admin_user):
    """Create test client with admin auth override."""

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
    """Create test client WITHOUT admin auth (no override for get_admin_user)."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Do NOT override get_admin_user — let real auth run
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_content(db_session):
    """Create sample content pieces."""
    pieces = [
        ContentPiece(
            slug="article-one",
            title="Article One",
            content_type="ARTICLE",
            body_md="# Article content",
            review_status="draft",
            created_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="published-post",
            title="Published Post",
            content_type="POST",
            body_md="# Post content",
            review_status="published",
            published_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="howto-guide",
            title="How-to Guide",
            content_type="HOWTO",
            body_md="# How-to content",
            review_status="pending_review",
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAdminAuth:
    """Tests for admin authentication on content endpoints."""

    def test_rejects_request_without_token(self, unauth_client):
        """Requests without Authorization header return 401."""
        response = unauth_client.get("/api/admin/content")
        assert response.status_code == 401

    def test_rejects_invalid_token(self, unauth_client):
        """Requests with invalid token return 401."""
        response = unauth_client.get(
            "/api/admin/content",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_rejects_non_admin_user(self, db_session, non_admin_user, monkeypatch):
        """Requests from non-admin users return 403."""
        # Set up ADMIN_EMAILS to only include admin email
        from apps.api import config as config_module

        original_settings = config_module.get_settings()
        monkeypatch.setattr(original_settings, "admin_emails", "admin@sinal.tech")

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Do NOT override get_admin_user
        try:
            client = TestClient(app)
            response = client.get(
                "/api/admin/content",
                headers={"Authorization": "Bearer non-admin-token"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestAdminListContent:
    """Tests for GET /api/admin/content."""

    def test_list_all_content(self, client, sample_content):
        """Lists all content regardless of status."""
        response = client.get("/api/admin/content")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_filter_by_type(self, client, sample_content):
        """Filters by content_type."""
        response = client.get("/api/admin/content?content_type=ARTICLE")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "article-one"

    def test_list_filter_by_status(self, client, sample_content):
        """Filters by review_status."""
        response = client.get("/api/admin/content?status=published")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "published-post"

    def test_list_search_by_title(self, client, sample_content):
        """Searches by title (case-insensitive)."""
        response = client.get("/api/admin/content?search=how-to")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "howto-guide"

    def test_list_pagination(self, client, sample_content):
        """Supports limit/offset pagination."""
        response = client.get("/api/admin/content?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2


class TestAdminCreateContent:
    """Tests for POST /api/admin/content."""

    def test_create_article(self, client):
        """Creates a new article with auto-generated slug."""
        payload = {
            "title": "Meu Primeiro Artigo",
            "body_md": "# Conteudo do artigo\n\nTexto aqui.",
            "content_type": "ARTICLE",
            "subtitle": "Um subtitulo",
            "summary": "Resumo do artigo",
            "meta_description": "Descricao para SEO",
            "sources": ["https://example.com"],
        }
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Meu Primeiro Artigo"
        assert data["slug"] == "meu-primeiro-artigo"
        assert data["content_type"] == "ARTICLE"
        assert data["review_status"] == "draft"
        assert data["body_md"] == "# Conteudo do artigo\n\nTexto aqui."
        assert data["subtitle"] == "Um subtitulo"
        assert data["sources"] == ["https://example.com"]

    def test_create_post(self, client):
        """Creates a POST type content."""
        payload = {
            "title": "Quick Update",
            "body_md": "Some content here.",
            "content_type": "POST",
        }
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 201
        assert response.json()["content_type"] == "POST"

    def test_create_howto(self, client):
        """Creates a HOWTO type content."""
        payload = {
            "title": "Como configurar seu ambiente",
            "body_md": "## Passo 1\n\nInstale as deps.",
            "content_type": "HOWTO",
        }
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 201
        assert response.json()["content_type"] == "HOWTO"

    def test_create_missing_title(self, client):
        """Missing title returns 422."""
        payload = {"body_md": "Some content"}
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 422

    def test_create_missing_body(self, client):
        """Missing body_md returns 422."""
        payload = {"title": "A Title"}
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 422

    def test_create_invalid_content_type(self, client):
        """Invalid content_type returns 422."""
        payload = {
            "title": "Test",
            "body_md": "Content",
            "content_type": "INVALID_TYPE",
        }
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 422

    def test_slug_uniqueness(self, client):
        """Duplicate titles get unique slugs with -2, -3 suffix."""
        payload = {"title": "Same Title", "body_md": "First content"}
        r1 = client.post("/api/admin/content", json=payload)
        r2 = client.post("/api/admin/content", json=payload)
        r3 = client.post("/api/admin/content", json=payload)

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r3.status_code == 201
        assert r1.json()["slug"] == "same-title"
        assert r2.json()["slug"] == "same-title-2"
        assert r3.json()["slug"] == "same-title-3"

    def test_slug_handles_accents(self, client):
        """Slugs handle Portuguese accented characters."""
        payload = {
            "title": "Tendências de IA na América Latina",
            "body_md": "Content",
        }
        response = client.post("/api/admin/content", json=payload)

        assert response.status_code == 201
        slug = response.json()["slug"]
        assert "ê" not in slug
        assert "é" not in slug
        assert "tendencias" in slug


class TestAdminGetContent:
    """Tests for GET /api/admin/content/{slug}."""

    def test_get_existing(self, client, sample_content):
        """Gets a content piece by slug."""
        response = client.get("/api/admin/content/article-one")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "article-one"
        assert data["body_md"] == "# Article content"

    def test_get_not_found(self, client):
        """Returns 404 for non-existent slug."""
        response = client.get("/api/admin/content/non-existent")

        assert response.status_code == 404


class TestAdminUpdateContent:
    """Tests for PATCH /api/admin/content/{slug}."""

    def test_update_title(self, client, sample_content):
        """Updates title and regenerates slug."""
        response = client.patch(
            "/api/admin/content/article-one",
            json={"title": "Updated Article Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Article Title"
        assert data["slug"] == "updated-article-title"

    def test_update_body(self, client, sample_content):
        """Updates body without changing slug."""
        response = client.patch(
            "/api/admin/content/article-one",
            json={"body_md": "# New body content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["body_md"] == "# New body content"
        assert data["slug"] == "article-one"  # Slug unchanged

    def test_update_partial(self, client, sample_content):
        """Partial update only changes specified fields."""
        response = client.patch(
            "/api/admin/content/article-one",
            json={"subtitle": "New subtitle"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subtitle"] == "New subtitle"
        assert data["title"] == "Article One"  # Unchanged

    def test_update_not_found(self, client):
        """Returns 404 for non-existent slug."""
        response = client.patch(
            "/api/admin/content/non-existent",
            json={"title": "Test"},
        )

        assert response.status_code == 404


class TestAdminDeleteContent:
    """Tests for DELETE /api/admin/content/{slug}."""

    def test_hard_delete_draft(self, client, db_session, sample_content):
        """Drafts are hard-deleted (removed from DB)."""
        response = client.delete("/api/admin/content/article-one")

        assert response.status_code == 204
        piece = db_session.query(ContentPiece).filter(ContentPiece.slug == "article-one").first()
        assert piece is None

    def test_soft_delete_published(self, client, db_session, sample_content):
        """Published content is soft-deleted (status → retracted)."""
        response = client.delete("/api/admin/content/published-post")

        assert response.status_code == 204
        piece = db_session.query(ContentPiece).filter(ContentPiece.slug == "published-post").first()
        assert piece is not None
        assert piece.review_status == "retracted"

    def test_delete_not_found(self, client):
        """Returns 404 for non-existent slug."""
        response = client.delete("/api/admin/content/non-existent")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Publish / Unpublish lifecycle
# ---------------------------------------------------------------------------


class TestAdminPublish:
    """Tests for POST /api/admin/content/{slug}/publish."""

    def test_publish_draft(self, client, sample_content):
        """Publishing a draft sets status=published and published_at."""
        response = client.post("/api/admin/content/article-one/publish")

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "published"
        assert data["published_at"] is not None

    def test_publish_already_published(self, client, sample_content):
        """Publishing already-published content returns 400."""
        response = client.post("/api/admin/content/published-post/publish")

        assert response.status_code == 400

    def test_publish_not_found(self, client):
        """Publishing non-existent content returns 404."""
        response = client.post("/api/admin/content/non-existent/publish")

        assert response.status_code == 404


class TestAdminUnpublish:
    """Tests for POST /api/admin/content/{slug}/unpublish."""

    def test_unpublish_published(self, client, sample_content):
        """Unpublishing sets status=draft and clears published_at."""
        response = client.post("/api/admin/content/published-post/unpublish")

        assert response.status_code == 200
        data = response.json()
        assert data["review_status"] == "draft"
        assert data["published_at"] is None

    def test_unpublish_draft(self, client, sample_content):
        """Unpublishing a draft returns 400."""
        response = client.post("/api/admin/content/article-one/unpublish")

        assert response.status_code == 400

    def test_unpublish_not_found(self, client):
        """Unpublishing non-existent content returns 404."""
        response = client.post("/api/admin/content/non-existent/unpublish")

        assert response.status_code == 404
