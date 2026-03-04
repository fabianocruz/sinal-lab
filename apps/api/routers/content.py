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
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import ContentDetailResponse, ContentResponse
from packages.database.models.content_piece import ContentPiece

router = APIRouter(prefix="/content", tags=["content"])


# No response_model — we return a dict envelope {items, total, limit, offset}
# instead of a bare list, so the frontend can handle pagination.
@router.get("")
def list_content(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    content_type_exclude: Optional[str] = Query(None, description="Exclude a content type"),
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
        query = query.filter(ContentPiece.content_type != content_type_exclude)
    if agent_name:
        query = query.filter(ContentPiece.agent_name == agent_name)
    if status:
        query = query.filter(ContentPiece.review_status == status)
    if search:
        query = query.filter(ContentPiece.title.ilike(f"%{search}%"))

    # Exclude future-dated content from published listings.
    if status == "published":
        now = datetime.now(timezone.utc)
        query = query.filter(
            (ContentPiece.published_at <= now)
            | (ContentPiece.published_at.is_(None))
        )

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
            ContentPiece.review_status == "published",
            ContentPiece.published_at <= now,
        )
        .order_by(desc(ContentPiece.published_at))
        .first()
    )
    if not newsletter:
        raise HTTPException(status_code=404, detail="Published newsletter not found")
    return newsletter


@router.get("/{slug}", response_model=ContentDetailResponse)
def get_content_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific content piece by slug (full detail including body)."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{slug}' not found")
    return piece
