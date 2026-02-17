"""Content router — list and retrieve published content."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import ContentDetailResponse, ContentResponse
from packages.database.models.content_piece import ContentPiece

router = APIRouter(prefix="/content", tags=["content"])


@router.get("", response_model=list[ContentResponse])
def list_content(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    agent_name: Optional[str] = Query(None, description="Filter by agent"),
    status: Optional[str] = Query(None, description="Filter by review status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List content pieces with optional filtering."""
    query = db.query(ContentPiece)

    if content_type:
        query = query.filter(ContentPiece.content_type == content_type)
    if agent_name:
        query = query.filter(ContentPiece.agent_name == agent_name)
    if status:
        query = query.filter(ContentPiece.review_status == status)

    pieces = (
        query.order_by(desc(ContentPiece.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return pieces


@router.get("/newsletter/latest", response_model=Optional[ContentResponse])
def get_latest_newsletter(db: Session = Depends(get_db)):
    """Get the most recently published newsletter."""
    newsletter = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.content_type == "DATA_REPORT",
            ContentPiece.agent_name == "sintese",
            ContentPiece.review_status == "published",
        )
        .order_by(desc(ContentPiece.published_at))
        .first()
    )
    if not newsletter:
        raise HTTPException(status_code=404, detail="No published newsletter found")
    return newsletter


@router.get("/{slug}", response_model=ContentDetailResponse)
def get_content_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific content piece by slug (full detail including body)."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{slug}' not found")
    return piece
