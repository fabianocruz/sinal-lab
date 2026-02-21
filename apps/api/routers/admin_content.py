"""Admin content router — CRUD operations for content management.

All endpoints require admin authentication via Bearer session token.
Admin status is determined by the ADMIN_EMAILS environment variable.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_admin_user, get_db
from apps.api.schemas.admin_content import (
    AdminContentResponse,
    ContentCreateRequest,
    ContentUpdateRequest,
)
from packages.database.models.content_piece import ContentPiece
from packages.database.models.user import User

router = APIRouter(prefix="/admin/content", tags=["admin"])


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ñ]", "n", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _unique_slug(db: Session, base_slug: str, exclude_id: Optional[uuid.UUID] = None) -> str:
    """Generate a unique slug, appending -2, -3, etc. if needed."""
    slug = base_slug
    counter = 1
    while True:
        query = db.query(ContentPiece).filter(ContentPiece.slug == slug)
        if exclude_id:
            query = query.filter(ContentPiece.id != exclude_id)
        if not query.first():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


@router.get("")
def admin_list_content(
    content_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """List all content pieces (any status) with filtering and pagination."""
    query = db.query(ContentPiece)

    if content_type:
        query = query.filter(ContentPiece.content_type == content_type)
    if status:
        query = query.filter(ContentPiece.review_status == status)
    if search:
        query = query.filter(ContentPiece.title.ilike(f"%{search}%"))

    total = query.count()
    pieces = (
        query.order_by(desc(ContentPiece.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [AdminContentResponse.model_validate(p) for p in pieces],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=AdminContentResponse, status_code=201)
def admin_create_content(
    body: ContentCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Create a new content piece. Slug is auto-generated from the title."""
    base_slug = _slugify(body.title)
    if not base_slug:
        raise HTTPException(status_code=400, detail="Titulo gera slug vazio.")

    slug = _unique_slug(db, base_slug)

    piece = ContentPiece(
        id=uuid.uuid4(),
        title=body.title,
        slug=slug,
        subtitle=body.subtitle,
        body_md=body.body_md,
        content_type=body.content_type,
        summary=body.summary,
        meta_description=body.meta_description,
        sources=body.sources,
        agent_name=None,
        review_status="draft",
    )
    db.add(piece)
    db.commit()
    db.refresh(piece)
    return piece


@router.get("/{slug}", response_model=AdminContentResponse)
def admin_get_content(
    slug: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Get a content piece by slug for editing."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Conteudo '{slug}' nao encontrado.")
    return piece


@router.patch("/{slug}", response_model=AdminContentResponse)
def admin_update_content(
    slug: str,
    body: ContentUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Partially update a content piece."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Conteudo '{slug}' nao encontrado.")

    update_data = body.model_dump(exclude_unset=True)

    # If title changed, regenerate slug
    if "title" in update_data:
        new_slug = _slugify(update_data["title"])
        if new_slug and new_slug != piece.slug:
            piece.slug = _unique_slug(db, new_slug, exclude_id=piece.id)

    for field, value in update_data.items():
        setattr(piece, field, value)

    db.commit()
    db.refresh(piece)
    return piece


@router.delete("/{slug}", status_code=204)
def admin_delete_content(
    slug: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Delete a content piece. Hard delete if draft, soft delete (retracted) otherwise."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Conteudo '{slug}' nao encontrado.")

    if piece.review_status == "draft":
        db.delete(piece)
    else:
        piece.review_status = "retracted"

    db.commit()


@router.post("/{slug}/publish", response_model=AdminContentResponse)
def admin_publish_content(
    slug: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Publish a content piece."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Conteudo '{slug}' nao encontrado.")

    if piece.review_status == "published":
        raise HTTPException(status_code=400, detail="Conteudo ja esta publicado.")

    piece.review_status = "published"
    piece.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(piece)
    return piece


@router.post("/{slug}/unpublish", response_model=AdminContentResponse)
def admin_unpublish_content(
    slug: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Unpublish a content piece (revert to draft)."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Conteudo '{slug}' nao encontrado.")

    if piece.review_status != "published":
        raise HTTPException(status_code=400, detail="Conteudo nao esta publicado.")

    piece.review_status = "draft"
    piece.published_at = None
    db.commit()
    db.refresh(piece)
    return piece
