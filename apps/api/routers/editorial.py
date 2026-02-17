"""Editorial pipeline router — review, approve, and inspect content."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.editorial.pipeline import EditorialPipeline
from packages.database.models.content_piece import ContentPiece

router = APIRouter(prefix="/editorial", tags=["editorial"])


class ReviewRequest(BaseModel):
    """Request to run editorial pipeline on content."""
    content_slug: str


class ReviewResponse(BaseModel):
    """Response from editorial pipeline review."""
    content_title: str
    agent_name: str
    run_id: str
    publish_ready: bool
    overall_grade: str
    blocker_count: int
    layers_run: int
    total_flags: int
    byline: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request to approve content for publication."""
    reviewer_name: Optional[str] = None
    notes: Optional[str] = None


@router.post("/review", response_model=ReviewResponse)
def review_content(
    request: ReviewRequest,
    db: Session = Depends(get_db),
):
    """Run a content piece through the editorial pipeline.

    Fetches the content from the database, builds an AgentOutput,
    and runs it through the 6-layer editorial governance pipeline.
    """
    piece = db.query(ContentPiece).filter(ContentPiece.slug == request.content_slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{request.content_slug}' not found")

    agent_output = AgentOutput(
        title=piece.title,
        body_md=piece.body_md or "",
        agent_name=piece.agent_name or "unknown",
        run_id=piece.slug,
        confidence=ConfidenceScore(
            data_quality=piece.confidence_dq or 0.5,
            analysis_confidence=piece.confidence_ac or 0.4,
            source_count=3,
        ),
        sources=[piece.slug],
        content_type=piece.content_type or "DATA_REPORT",
        summary=piece.summary,
    )

    pipeline = EditorialPipeline(halt_on_blocker=False)
    result = pipeline.review(agent_output)

    return ReviewResponse(
        content_title=result.content_title,
        agent_name=result.agent_name,
        run_id=result.run_id,
        publish_ready=result.publish_ready,
        overall_grade=result.overall_grade,
        blocker_count=result.blocker_count,
        layers_run=len(result.layer_results),
        total_flags=len(result.all_flags),
        byline=result.byline,
    )


@router.get("/queue")
def get_review_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List content pending human review (draft or review status)."""
    pieces = (
        db.query(ContentPiece)
        .filter(ContentPiece.review_status.in_(["draft", "review"]))
        .order_by(desc(ContentPiece.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(piece.id),
            "title": piece.title,
            "slug": piece.slug,
            "content_type": piece.content_type,
            "agent_name": piece.agent_name,
            "review_status": piece.review_status,
            "confidence_dq": piece.confidence_dq,
            "confidence_ac": piece.confidence_ac,
        }
        for piece in pieces
    ]


@router.post("/approve/{slug}")
def approve_content(
    slug: str,
    request: ApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve content for publication after human review."""
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{slug}' not found")

    if piece.review_status == "published":
        raise HTTPException(status_code=400, detail="Content is already published")

    from datetime import datetime, timezone
    piece.review_status = "published"
    piece.published_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "message": f"Content '{slug}' approved and published",
        "slug": slug,
        "review_status": "published",
        "reviewer": request.reviewer_name,
    }


@router.get("/history/{slug}")
def get_editorial_history(
    slug: str,
    db: Session = Depends(get_db),
):
    """Get editorial review history for a content piece.

    Placeholder — in production this would query a revision
    history table. For now, returns basic content metadata.
    """
    piece = db.query(ContentPiece).filter(ContentPiece.slug == slug).first()
    if not piece:
        raise HTTPException(status_code=404, detail=f"Content '{slug}' not found")

    return {
        "slug": slug,
        "title": piece.title,
        "review_status": piece.review_status,
        "content_type": piece.content_type,
        "agent_name": piece.agent_name,
        "created_at": piece.created_at.isoformat() if piece.created_at else None,
        "published_at": piece.published_at.isoformat() if piece.published_at else None,
        "revisions": [
            {
                "action": "created",
                "timestamp": piece.created_at.isoformat() if piece.created_at else None,
                "by": piece.agent_name or "system",
            }
        ],
    }
