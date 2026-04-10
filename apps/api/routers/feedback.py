"""Feedback API — collect NPS scores and comments.

Public endpoint (no auth required) for collecting feedback from
newsletter emails, dashboard widgets, and feed interactions.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from apps.api.deps import get_db
from packages.database.models.feedback import Feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    """Submit feedback."""

    nps_score: int = Field(..., ge=0, le=10, description="NPS score 0-10")
    comment: Optional[str] = Field(None, max_length=2000)
    source: str = Field("newsletter", description="newsletter, dashboard, feed")
    content_slug: Optional[str] = Field(None, description="e.g. sinal-semanal-53")
    edition: Optional[int] = Field(None, description="Newsletter edition number")
    user_email: Optional[str] = None
    session_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    ok: bool = True
    message: str = "Obrigado pelo feedback!"


class FeedbackStats(BaseModel):
    """Aggregated feedback stats."""

    total_responses: int
    avg_nps: float
    promoters: int  # 9-10
    passives: int  # 7-8
    detractors: int  # 0-6
    nps_net: float  # (promoters - detractors) / total * 100


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
):
    """Submit NPS feedback. No authentication required."""
    feedback = Feedback(
        nps_score=body.nps_score,
        comment=body.comment,
        source=body.source,
        content_slug=body.content_slug,
        edition=body.edition,
        user_email=body.user_email,
        session_id=body.session_id,
    )
    db.add(feedback)
    db.commit()

    logger.info(
        "Feedback received: nps=%d source=%s edition=%s",
        body.nps_score, body.source, body.edition,
    )

    return FeedbackResponse()


@router.get("/stats", response_model=FeedbackStats)
def get_feedback_stats(
    source: Optional[str] = Query(None),
    edition: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregated feedback stats."""
    query = db.query(Feedback)
    if source:
        query = query.filter(Feedback.source == source)
    if edition:
        query = query.filter(Feedback.edition == edition)

    total = query.count()
    if total == 0:
        return FeedbackStats(
            total_responses=0, avg_nps=0.0,
            promoters=0, passives=0, detractors=0, nps_net=0.0,
        )

    avg = db.query(func.avg(Feedback.nps_score)).filter(
        *([Feedback.source == source] if source else []),
        *([Feedback.edition == edition] if edition else []),
    ).scalar() or 0.0

    promoters = query.filter(Feedback.nps_score >= 9).count()
    passives = query.filter(Feedback.nps_score.between(7, 8)).count()
    detractors = query.filter(Feedback.nps_score <= 6).count()
    nps_net = round((promoters - detractors) / total * 100, 1)

    return FeedbackStats(
        total_responses=total,
        avg_nps=round(float(avg), 1),
        promoters=promoters,
        passives=passives,
        detractors=detractors,
        nps_net=nps_net,
    )


@router.get("/unprocessed")
def get_unprocessed_feedback(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get unprocessed feedback for AutoPMF loop."""
    entries = (
        db.query(Feedback)
        .filter(Feedback.processed == False)
        .order_by(Feedback.created_at.asc())
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": str(e.id),
                "nps_score": e.nps_score,
                "comment": e.comment,
                "source": e.source,
                "edition": e.edition,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": len(entries),
    }
