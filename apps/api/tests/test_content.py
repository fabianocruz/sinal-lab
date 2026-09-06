"""Tests for content router.

Uses SQLite in-memory with StaticPool so all threads share the same
database connection. This is required because FastAPI runs sync endpoints
in a worker thread pool — without StaticPool, each thread would get a
separate in-memory database and see "no such table" errors.

Run: pytest apps/api/tests/test_content.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.api.deps import get_db
from packages.database.models.base import Base
from packages.database.models.content_piece import ContentPiece
from packages.database.models.session import SessionDB
from packages.database.models.user import User


# StaticPool ensures all threads share a single connection to the in-memory DB.
# Without it, FastAPI's thread pool creates separate connections that can't
# see each other's tables. See: https://sqlalche.me/e/20/e3q8
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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


@pytest.fixture
def sample_content(db_session):
    """Create sample content pieces for testing."""
    pieces = [
        ContentPiece(
            slug="newsletter-edition-1",
            title="Newsletter Edition #1",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_md="# Newsletter content",
            confidence_dq=0.85,
            confidence_ac=0.78,
            review_status="published",
            published_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="trend-ai-agents-2026",
            title="AI Agents Rising in 2026",
            content_type="TREND_ANALYSIS",
            agent_name="radar",
            body_md="# Trend analysis content",
            confidence_dq=0.72,
            confidence_ac=0.68,
            review_status="published",
            published_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ContentPiece(
            slug="draft-article",
            title="Draft Article",
            content_type="ARTICLE",
            agent_name="codigo",
            body_md="# Draft content",
            confidence_dq=0.65,
            confidence_ac=0.60,
            review_status="pending",
            published_at=None,
            created_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


def test_list_content_all(client, sample_content):
    """Test listing all content pieces returns paginated response."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_content_filter_by_type(client, sample_content):
    """Test filtering content by type."""
    response = client.get("/api/content?content_type=DATA_REPORT")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "newsletter-edition-1"


def test_list_content_exclude_by_type(client, sample_content):
    """Test excluding content by type (content_type_exclude)."""
    response = client.get("/api/content?content_type_exclude=ARTICLE")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(c["content_type"] != "ARTICLE" for c in data["items"])


def test_list_content_exclude_multiple_types(client, db_session, sample_content):
    """Test excluding multiple content types with comma-separated values."""
    # Add an INTELLIGENCE piece to the existing sample data
    intel = ContentPiece(
        slug="devtools-intelligence",
        title="DevTools Intelligence Report",
        content_type="INTELLIGENCE",
        agent_name="mercado",
        body_md="# Intelligence report",
        review_status="published",
        published_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(intel)
    db_session.commit()

    # Exclude both ARTICLE and INTELLIGENCE
    response = client.get("/api/content?content_type_exclude=ARTICLE,INTELLIGENCE")
    assert response.status_code == 200
    data = response.json()
    types = {c["content_type"] for c in data["items"]}
    assert "ARTICLE" not in types
    assert "INTELLIGENCE" not in types
    assert data["total"] == 2  # DATA_REPORT + TREND_ANALYSIS


def test_list_content_filter_by_agent(client, sample_content):
    """Test filtering content by agent."""
    response = client.get("/api/content?agent_name=radar")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["agent_name"] == "radar"


def test_list_content_filter_by_status(client, sample_content):
    """Test filtering content by review status."""
    response = client.get("/api/content?status=published")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(c["review_status"] == "published" for c in data["items"])


def test_list_content_search(client, sample_content):
    """Test searching content by title."""
    response = client.get("/api/content?search=Newsletter")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "newsletter-edition-1"


def test_list_content_pagination(client, sample_content):
    """Test content pagination."""
    response = client.get("/api/content?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Second page
    response2 = client.get("/api/content?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_content_limit_validation(client, sample_content):
    """Test limit validation."""
    # Too high
    response = client.get("/api/content?limit=200")
    assert response.status_code == 422

    # Too low
    response = client.get("/api/content?limit=0")
    assert response.status_code == 422


def test_get_latest_newsletter_success(client, sample_content):
    """Test getting the latest published newsletter."""
    response = client.get("/api/content/newsletter/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "newsletter-edition-1"
    assert data["content_type"] == "DATA_REPORT"


def test_get_latest_newsletter_not_found(client):
    """Test getting latest newsletter when none exists."""
    response = client.get("/api/content/newsletter/latest")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_content_by_slug_success(client, sample_content):
    """Test getting content by slug."""
    response = client.get("/api/content/newsletter-edition-1")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "newsletter-edition-1"
    assert data["title"] == "Newsletter Edition #1"
    assert "body_md" in data


def test_get_content_by_slug_not_found(client, sample_content):
    """Test getting non-existent content."""
    response = client.get("/api/content/non-existent-slug")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_content_ordering(client, sample_content):
    """Test that content is ordered by published_at descending."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    items = data["items"]

    # Verify descending order by published_at (most recent first)
    # newsletter-edition-1 has published_at=Feb 15 (latest)
    assert items[0]["slug"] == "newsletter-edition-1"


def test_content_response_schema(client, sample_content):
    """Test content response includes all required fields."""
    response = client.get("/api/content")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0

    item = data["items"][0]
    required_fields = {
        "slug", "title", "content_type", "agent_name",
        "confidence_dq", "confidence_ac", "review_status"
    }
    assert required_fields.issubset(set(item.keys()))


# --- Rich newsletter metadata_ tests ---


def test_get_content_by_slug_includes_metadata(client, db_session):
    """Test that detail endpoint includes metadata_ when populated."""
    piece = ContentPiece(
        slug="rich-newsletter-1",
        title="Rich Newsletter #1",
        content_type="DATA_REPORT",
        agent_name="sintese",
        body_md="# Rich content",
        review_status="published",
        published_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        metadata_={
            "hero_image": {"url": "https://img.example.com/hero.jpg", "alt": "Hero"},
            "reading_time_minutes": 4,
            "callouts": [{"type": "highlight", "content": "Key insight", "position": "after_intro"}],
            "companies_mentioned": ["Nubank", "Rappi"],
        },
    )
    db_session.add(piece)
    db_session.commit()

    response = client.get("/api/content/rich-newsletter-1")
    assert response.status_code == 200
    data = response.json()

    assert "metadata_" in data
    assert data["metadata_"] is not None
    assert data["metadata_"]["hero_image"]["url"] == "https://img.example.com/hero.jpg"
    assert data["metadata_"]["reading_time_minutes"] == 4
    assert len(data["metadata_"]["callouts"]) == 1
    assert data["metadata_"]["companies_mentioned"] == ["Nubank", "Rappi"]


def test_get_content_by_slug_metadata_null_when_not_set(client, sample_content):
    """Test that detail endpoint returns metadata_=null when not populated."""
    response = client.get("/api/content/newsletter-edition-1")
    assert response.status_code == 200
    data = response.json()

    assert "metadata_" in data
    assert data["metadata_"] is None


def test_list_content_includes_metadata(client, db_session):
    """Test that list endpoint includes metadata_ for rich card subtitles."""
    piece = ContentPiece(
        slug="list-metadata-test",
        title="List Metadata Test",
        content_type="DATA_REPORT",
        agent_name="sintese",
        body_md="# Body",
        review_status="published",
        published_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
        metadata_={"hero_image": {"url": "https://img.example.com/hero.jpg", "alt": "Hero"}},
    )
    db_session.add(piece)
    db_session.commit()

    response = client.get("/api/content")
    assert response.status_code == 200
    data = response.json()

    for item in data["items"]:
        assert "metadata_" in item
    assert data["items"][0]["metadata_"]["hero_image"]["url"] == "https://img.example.com/hero.jpg"


# ---------------------------------------------------------------------------
# Detail endpoint visibility — unpublished content must not leak
#
# GET /api/content/{slug} is public. Only review_status='published' pieces
# may be served; anything else must be indistinguishable from a missing slug.
# The team previews unpublished pieces with ?preview=true + admin credentials.
# ---------------------------------------------------------------------------

ADMIN_EMAIL = "admin@sinal.tech"
ADMIN_SECRET = "test-admin-secret"

# Every review_status a piece can hold that is NOT publicly readable.
# See packages/database/models/content_piece.py.
NON_PUBLIC_STATUSES = ["draft", "pending_review", "approved", "retracted"]

SECRET_BODY_MARKER = "SEGREDO-EDITORIAL"


def _slug_for(status: str) -> str:
    """Slug used by the unpublished_content fixture for a given status."""
    return f"{status.replace('_', '-')}-piece"


def _not_found_body(slug: str) -> dict[str, str]:
    """Expected 404 payload — identical shape for missing and unpublished."""
    return {"detail": f"Content '{slug}' not found"}


@pytest.fixture
def unpublished_content(db_session) -> list[ContentPiece]:
    """One piece per non-public review_status + a scheduled (future) piece."""
    created = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
    pieces = [
        ContentPiece(
            slug=_slug_for(status),
            title=f"Unreleased piece ({status})",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_md=f"# {SECRET_BODY_MARKER} {status}",
            review_status=status,
            published_at=None,
            created_at=created,
            updated_at=created,
        )
        for status in NON_PUBLIC_STATUSES
    ]

    # Published but scheduled for the future — same class of leak as a draft.
    pieces.append(
        ContentPiece(
            slug="scheduled-piece",
            title="Scheduled piece",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_md=f"# {SECRET_BODY_MARKER} scheduled",
            review_status="published",
            published_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_at=created,
            updated_at=created,
        )
    )

    # Published with no published_at — must stay readable (mirrors list filter).
    pieces.append(
        ContentPiece(
            slug="published-no-date-piece",
            title="Published without date",
            content_type="DATA_REPORT",
            agent_name="sintese",
            body_md="# Public body",
            review_status="published",
            published_at=None,
            created_at=created,
            updated_at=created,
        )
    )

    for piece in pieces:
        db_session.add(piece)
    db_session.commit()
    return pieces


@pytest.fixture
def admin_user(db_session, monkeypatch) -> User:
    """Configure ADMIN_EMAILS/ADMIN_API_SECRET and create the admin user row."""
    from apps.api import config as config_module

    settings = config_module.get_settings()
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "admin_api_secret", ADMIN_SECRET)

    user = User(
        id=uuid.uuid4(),
        email=ADMIN_EMAIL,
        name="Admin User",
        auth_provider="email",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_headers(admin_user) -> dict[str, str]:
    """Service-to-service admin headers (Next.js proxy method)."""
    return {"X-Admin-Email": ADMIN_EMAIL, "X-Admin-Secret": ADMIN_SECRET}


@pytest.fixture
def admin_bearer_headers(db_session, admin_user) -> dict[str, str]:
    """Bearer session token belonging to the admin user."""
    session = SessionDB(
        id=uuid.uuid4(),
        session_token="admin-session-token",
        user_id=admin_user.id,
        expires=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()
    return {"Authorization": "Bearer admin-session-token"}


@pytest.fixture
def non_admin_bearer_headers(db_session, admin_user) -> dict[str, str]:
    """Valid session token for a user who is NOT in ADMIN_EMAILS."""
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
        session_token="non-admin-session-token",
        user_id=user.id,
        expires=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()
    return {"Authorization": "Bearer non-admin-session-token"}


class TestContentDetailHidesUnpublished:
    """GET /api/content/{slug} must only serve published content.

    The published happy path and the missing-slug 404 are covered by
    test_get_content_by_slug_success / test_get_content_by_slug_not_found.
    """

    def test_published_without_published_at_returns_200(
        self, client, unpublished_content
    ):
        """published_at IS NULL stays visible — same rule as the list endpoint."""
        response = client.get("/api/content/published-no-date-piece")

        assert response.status_code == 200
        assert response.json()["slug"] == "published-no-date-piece"

    @pytest.mark.parametrize("status", NON_PUBLIC_STATUSES)
    def test_non_published_status_returns_404(
        self, client, unpublished_content, status
    ):
        slug = _slug_for(status)
        response = client.get(f"/api/content/{slug}")

        assert response.status_code == 404
        assert response.json() == _not_found_body(slug)

    @pytest.mark.parametrize("status", NON_PUBLIC_STATUSES)
    def test_non_published_body_is_never_served(
        self, client, unpublished_content, status
    ):
        response = client.get(f"/api/content/{_slug_for(status)}")

        assert SECRET_BODY_MARKER not in response.text

    def test_scheduled_future_publication_returns_404(
        self, client, unpublished_content
    ):
        """review_status='published' with a future published_at is embargoed."""
        response = client.get("/api/content/scheduled-piece")

        assert response.status_code == 404
        assert response.json() == _not_found_body("scheduled-piece")
        assert SECRET_BODY_MARKER not in response.text

    def test_unpublished_is_indistinguishable_from_missing(
        self, client, unpublished_content
    ):
        """An outsider cannot tell 'exists but unpublished' from 'does not exist'."""
        unpublished = client.get("/api/content/draft-piece")
        missing = client.get("/api/content/ghost-piece")

        assert unpublished.status_code == missing.status_code == 404
        assert unpublished.json().keys() == missing.json().keys()
        # Bodies match apart from the slug the caller supplied themselves.
        assert unpublished.json() == _not_found_body("draft-piece")
        assert missing.json() == _not_found_body("ghost-piece")

    def test_unrelated_bearer_token_still_reads_published(
        self, client, sample_content
    ):
        """Public API-key callers (documented in api-docs.ts) must not break."""
        response = client.get(
            "/api/content/newsletter-edition-1",
            headers={"Authorization": "Bearer sk_live_not_a_session"},
        )

        assert response.status_code == 200
        assert response.json()["slug"] == "newsletter-edition-1"


class TestContentDetailPreviewBypass:
    """?preview=true is honoured only for authenticated admins."""

    def test_admin_headers_preview_returns_unpublished(
        self, client, unpublished_content, admin_headers
    ):
        response = client.get(
            "/api/content/pending-review-piece?preview=true", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "pending-review-piece"
        assert data["review_status"] == "pending_review"
        assert SECRET_BODY_MARKER in data["body_md"]

    def test_admin_bearer_preview_returns_unpublished(
        self, client, unpublished_content, admin_bearer_headers
    ):
        response = client.get(
            "/api/content/draft-piece?preview=true", headers=admin_bearer_headers
        )

        assert response.status_code == 200
        assert response.json()["slug"] == "draft-piece"

    def test_admin_preview_returns_scheduled_piece(
        self, client, unpublished_content, admin_headers
    ):
        response = client.get(
            "/api/content/scheduled-piece?preview=true", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["slug"] == "scheduled-piece"

    def test_preview_without_credentials_returns_404(
        self, client, unpublished_content
    ):
        """Closed by default: the flag alone grants nothing."""
        response = client.get("/api/content/approved-piece?preview=true")

        assert response.status_code == 404
        assert response.json() == _not_found_body("approved-piece")

    def test_preview_ignores_api_env(
        self, client, unpublished_content, monkeypatch
    ):
        """The bypass is credential-based, so no environment can open it."""
        from apps.api import config as config_module

        monkeypatch.setattr(config_module.get_settings(), "api_env", "development")

        response = client.get("/api/content/draft-piece?preview=true")

        assert response.status_code == 404

    def test_preview_with_wrong_secret_returns_404(
        self, client, unpublished_content, admin_user
    ):
        """Bad credentials must 404, not 401/403 — no existence disclosure."""
        response = client.get(
            "/api/content/draft-piece?preview=true",
            headers={"X-Admin-Email": ADMIN_EMAIL, "X-Admin-Secret": "wrong-secret"},
        )

        assert response.status_code == 404
        assert response.json() == _not_found_body("draft-piece")

    def test_preview_with_non_admin_session_returns_404(
        self, client, unpublished_content, non_admin_bearer_headers
    ):
        response = client.get(
            "/api/content/draft-piece?preview=true", headers=non_admin_bearer_headers
        )

        assert response.status_code == 404
        assert response.json() == _not_found_body("draft-piece")

    def test_admin_without_preview_flag_returns_404(
        self, client, unpublished_content, admin_headers
    ):
        """Opt-in only: admin credentials alone keep the public view."""
        response = client.get("/api/content/draft-piece", headers=admin_headers)

        assert response.status_code == 404
        assert response.json() == _not_found_body("draft-piece")

    def test_preview_on_published_piece_is_unchanged(
        self, client, sample_content, admin_headers
    ):
        response = client.get(
            "/api/content/newsletter-edition-1?preview=true", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["slug"] == "newsletter-edition-1"

    def test_preview_on_missing_slug_returns_404(
        self, client, unpublished_content, admin_headers
    ):
        response = client.get(
            "/api/content/ghost-piece?preview=true", headers=admin_headers
        )

        assert response.status_code == 404
        assert response.json() == _not_found_body("ghost-piece")
