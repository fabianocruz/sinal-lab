"""Content router — list and retrieve published content.

Response format for GET /api/content (paginated):
    {
        "items": [ContentResponse, ...],
        "total": <int>,    # total matching records (before pagination)
        "limit": <int>,    # page size
        "offset": <int>    # current offset
    }

The frontend (apps/web/lib/api.ts) expects this paginated envelope.
Individual endpoints (/{slug}, /newsletter/latest) return a single object.

Visibility: every endpoint here is public, so /{slug} and /newsletter/latest
only serve review_status='published' pieces. The list endpoint keeps its
caller-supplied ``status`` filter (the frontend relies on it), which still
lets anyone enumerate unreleased pieces — but only their metadata, since the
list schema (ContentResponse) has no body_md.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from apps.api.deps import get_db, optional_admin_user
from apps.api.schemas.common import ContentDetailResponse, ContentResponse
from packages.database.models.content_piece import ContentPiece
from packages.database.models.user import User

router = APIRouter(prefix="/content", tags=["content"])

# Only pieces in this review_status are readable through the public endpoints.
# Everything else (draft, pending_review, approved, retracted) is unreleased
# editorial material — see packages/database/models/content_piece.py.
PUBLIC_REVIEW_STATUS = "published"


def _within_publication_window(query: OrmQuery) -> OrmQuery:
    """Exclude pieces scheduled for a future date.

    ``published_at IS NULL`` is kept visible: some published pieces predate
    the scheduling workflow and carry no date.
    """
    now = datetime.now(timezone.utc)
    return query.filter(
        (ContentPiece.published_at <= now) | (ContentPiece.published_at.is_(None))
    )


# No response_model — we return a dict envelope {items, total, limit, offset}
# instead of a bare list, so the frontend can handle pagination.
@router.get("")
def list_content(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    content_type_exclude: Optional[str] = Query(None, description="Exclude content types (comma-separated)"),
    agent_name: Optional[str] = Query(None, description="Filter by agent"),
    status: Optional[str] = Query(None, description="Filter by review status"),
    search: Optional[str] = Query(None, description="Case-insensitive title search (LIKE)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List content pieces with optional filtering and pagination."""
    query = db.query(ContentPiece)

    if content_type:
        query = query.filter(ContentPiece.content_type == content_type)
    if content_type_exclude:
        excluded = [t.strip() for t in content_type_exclude.split(",") if t.strip()]
        if len(excluded) == 1:
            query = query.filter(ContentPiece.content_type != excluded[0])
        elif excluded:
            query = query.filter(ContentPiece.content_type.notin_(excluded))
    if agent_name:
        query = query.filter(ContentPiece.agent_name == agent_name)
    if status:
        query = query.filter(ContentPiece.review_status == status)
    if search:
        query = query.filter(ContentPiece.title.ilike(f"%{search}%"))

    # Exclude future-dated content from published listings.
    if status == PUBLIC_REVIEW_STATUS:
        query = _within_publication_window(query)

    total = query.count()
    pieces = (
        query.order_by(desc(ContentPiece.published_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [ContentResponse.model_validate(p) for p in pieces],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/newsletter/latest", response_model=Optional[ContentResponse])
def get_latest_newsletter(db: Session = Depends(get_db)):
    """Get the most recently published newsletter."""
    now = datetime.now(timezone.utc)
    newsletter = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.content_type == "DATA_REPORT",
            ContentPiece.agent_name == "sintese",
            ContentPiece.review_status == PUBLIC_REVIEW_STATUS,
            ContentPiece.published_at <= now,
        )
        .order_by(desc(ContentPiece.published_at))
        .first()
    )
    if not newsletter:
        raise HTTPException(status_code=404, detail="Published newsletter not found")
    return newsletter


@router.get("/{slug}", response_model=ContentDetailResponse)
def get_content_by_slug(
    slug: str,
    preview: bool = Query(
        False,
        description="Preview unreleased content. Requires admin credentials; "
        "ignored otherwise.",
    ),
    db: Session = Depends(get_db),
    admin: Optional[User] = Depends(optional_admin_user),
) -> ContentPiece:
    """Get a specific content piece by slug (full detail including body).

    Public callers only ever see pieces with ``review_status='published'``
    whose ``published_at`` has arrived (or is NULL) — same rule as the list
    and ``/newsletter/latest`` endpoints. Anything else returns the exact
    same 404 payload as a slug that does not exist, so unreleased drafts
    cannot be enumerated.

    **Preview bypass (team only).** Pass ``?preview=true`` together with
    admin credentials, either:

    - ``X-Admin-Email`` + ``X-Admin-Secret`` (ADMIN_API_SECRET), or
    - ``Authorization: Bearer <session_token>`` for a user in ADMIN_EMAILS.

    The bypass is credential-based, not environment-based: without valid
    admin credentials it is closed in every environment, including
    production, and invalid credentials fall through to the public 404
    (never 401/403) so the response never confirms that the slug exists.
    """
    query = db.query(ContentPiece).filter(ContentPiece.slug == slug)

    if not (preview and admin is not None):
        query = _within_publication_window(
            query.filter(ContentPiece.review_status == PUBLIC_REVIEW_STATUS)
        )

    piece = query.first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{slug}' not found")
    return piece
