"""Waitlist router — founding member signup and count."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import WaitlistCountResponse, WaitlistResponse, WaitlistSignup
from packages.database.models.user import User

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.post("", response_model=WaitlistResponse)
def signup_waitlist(
    body: WaitlistSignup,
    db: Session = Depends(get_db),
):
    """Add an email to the founding member waitlist."""
    email = body.email.strip().lower()

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Email inválido.")

    # Check if already signed up
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email já cadastrado na waitlist.")

    # Determine position
    current_count = db.query(func.count(User.id)).scalar() or 0
    position = current_count + 1

    user = User(
        id=uuid.uuid4(),
        email=email,
        name=body.name,
        role=body.role,
        company=body.company,
        waitlist_position=position,
        status="waitlist",
    )
    db.add(user)
    db.commit()

    return WaitlistResponse(
        message="Você está na lista! Fique de olho no seu email.",
        position=position,
    )


@router.get("/count", response_model=WaitlistCountResponse)
def waitlist_count(db: Session = Depends(get_db)):
    """Get the current waitlist size (public)."""
    count = db.query(func.count(User.id)).filter(User.status == "waitlist").scalar() or 0
    return WaitlistCountResponse(count=count)


@router.get("/list")
def list_waitlist_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all waitlist signups (admin only).

    NOTE: This endpoint exposes PII and should be protected with
    authentication before deploying to production.
    """
    from sqlalchemy import asc

    users = (
        db.query(User)
        .filter(User.status == "waitlist")
        .order_by(asc(User.waitlist_position))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "company": user.company,
            "waitlist_position": user.waitlist_position,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]
