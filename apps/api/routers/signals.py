"""Signals router — Social Signal Intelligence dashboard endpoints.

Response format for paginated endpoints:
    {
        "items": [...],
        "total": <int>,    # total matching records (before pagination)
        "limit": <int>,    # page size
        "offset": <int>    # current offset
    }

Run: pytest apps/api/tests/test_signals.py -v
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from packages.database.models.monitored_account import MonitoredAccount
from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.social_signal import SocialSignal
from packages.database.models.weekly_pulse import WeeklyPulse

router = APIRouter(prefix="/signals", tags=["signals"])


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------


class SocialSignalResponse(BaseModel):
    """Social signal response schema (list view)."""

    id: UUID
    platform: str
    post_url: str
    author_handle: Optional[str] = None
    author_display_name: Optional[str] = None
    text: Optional[str] = None
    content_hash: str
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    metrics: Optional[Dict[str, Any]] = None
    theme: Optional[str] = None
    sub_theme: Optional[str] = None
    entities: Optional[List[Dict[str, Any]]] = None
    sentiment: Optional[float] = None
    authority_score: Optional[float] = None
    signal_dimensions: Optional[Dict[str, Any]] = None
    cluster_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SignalClusterResponse(BaseModel):
    """Signal cluster response schema (list view)."""

    id: UUID
    name: str
    slug: str
    theme: Optional[str] = None
    sub_theme: Optional[str] = None
    description: Optional[str] = None
    signal_count: int = 0
    composite_score: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    narrative_stage: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    top_voices: Optional[List[Dict[str, Any]]] = None
    top_posts: Optional[List[Dict[str, Any]]] = None
    related_companies: Optional[List[Dict[str, Any]]] = None
    week_number: Optional[int] = None
    year: Optional[int] = None
    agent_run_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WeeklyPulseResponse(BaseModel):
    """Weekly pulse response schema."""

    id: UUID
    week_number: int
    year: int
    slug: str
    accelerating_themes: Optional[List[Dict[str, Any]]] = None
    emerging_signals: Optional[List[Dict[str, Any]]] = None
    top_posts: Optional[List[Dict[str, Any]]] = None
    top_voices: Optional[List[Dict[str, Any]]] = None
    startups_to_watch: Optional[List[Dict[str, Any]]] = None
    sector_implications: Optional[List[Dict[str, Any]]] = None
    generated_at: Optional[datetime] = None
    agent_run_id: Optional[str] = None
    status: str = "draft"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MonitoredAccountResponse(BaseModel):
    """Monitored account response schema (list view)."""

    id: UUID
    platform: str
    handle: str
    display_name: Optional[str] = None
    account_type: Optional[str] = None
    sector_tags: Optional[list] = None
    authority_score: float = 0.5
    follower_count: Optional[int] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None
    is_active: bool = True
    last_fetched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SignalStatsResponse(BaseModel):
    """Aggregate stats for the signals dashboard."""

    total_signals: int
    total_clusters: int
    total_voices: int
    platforms: Dict[str, int]
    themes: Dict[str, int]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_signals(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    theme: Optional[str] = Query(None, description="Filter by theme"),
    sub_theme: Optional[str] = Query(None, description="Filter by sub-theme"),
    date_from: Optional[datetime] = Query(None, description="Filter signals published after this datetime"),
    date_to: Optional[datetime] = Query(None, description="Filter signals published before this datetime"),
    search: Optional[str] = Query(None, description="Case-insensitive text search (LIKE)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List social signals with optional filtering and pagination."""
    query = db.query(SocialSignal)

    if platform:
        query = query.filter(SocialSignal.platform == platform)
    if theme:
        query = query.filter(SocialSignal.theme == theme)
    if sub_theme:
        query = query.filter(SocialSignal.sub_theme == sub_theme)
    if date_from:
        query = query.filter(SocialSignal.published_at >= date_from)
    if date_to:
        query = query.filter(SocialSignal.published_at <= date_to)
    if search:
        query = query.filter(SocialSignal.text.ilike(f"%{search}%"))

    total = query.count()
    signals = (
        query.order_by(desc(SocialSignal.published_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [SocialSignalResponse.model_validate(s) for s in signals],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/clusters")
def list_clusters(
    theme: Optional[str] = Query(None, description="Filter by theme"),
    narrative_stage: Optional[str] = Query(None, description="Filter by narrative stage"),
    week_number: Optional[int] = Query(None, description="Filter by week number"),
    year: Optional[int] = Query(None, description="Filter by year"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List signal clusters with optional filtering and pagination."""
    query = db.query(SignalCluster)

    if theme:
        query = query.filter(SignalCluster.theme == theme)
    if narrative_stage:
        query = query.filter(SignalCluster.narrative_stage == narrative_stage)
    if week_number is not None:
        query = query.filter(SignalCluster.week_number == week_number)
    if year is not None:
        query = query.filter(SignalCluster.year == year)

    total = query.count()
    clusters = (
        query.order_by(desc(SignalCluster.composite_score))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [SignalClusterResponse.model_validate(c) for c in clusters],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/clusters/{slug}", response_model=SignalClusterResponse)
def get_cluster_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific signal cluster by slug."""
    cluster = db.query(SignalCluster).filter(SignalCluster.slug == slug).first()
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{slug}' not found")
    return cluster


@router.get("/pulse")
def get_latest_pulse(
    week: Optional[int] = Query(None, description="Specific week number"),
    year: Optional[int] = Query(None, description="Specific year"),
    db: Session = Depends(get_db),
):
    """Get the latest weekly pulse, or a specific one by week/year."""
    query = db.query(WeeklyPulse)

    if week is not None and year is not None:
        pulse = query.filter(
            WeeklyPulse.week_number == week,
            WeeklyPulse.year == year,
        ).first()
    else:
        pulse = query.order_by(
            desc(WeeklyPulse.year),
            desc(WeeklyPulse.week_number),
        ).first()

    if not pulse:
        raise HTTPException(status_code=404, detail="Weekly pulse not found")
    return WeeklyPulseResponse.model_validate(pulse)


@router.get("/pulse/{slug}", response_model=WeeklyPulseResponse)
def get_pulse_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific weekly pulse by slug."""
    pulse = db.query(WeeklyPulse).filter(WeeklyPulse.slug == slug).first()
    if not pulse:
        raise HTTPException(status_code=404, detail=f"Pulse '{slug}' not found")
    return pulse


@router.get("/voices")
def list_voices(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List monitored accounts (voices) with optional filtering and pagination."""
    query = db.query(MonitoredAccount)

    if platform:
        query = query.filter(MonitoredAccount.platform == platform)
    if account_type:
        query = query.filter(MonitoredAccount.account_type == account_type)
    if is_active is not None:
        query = query.filter(MonitoredAccount.is_active == is_active)

    total = query.count()
    accounts = (
        query.order_by(desc(MonitoredAccount.authority_score))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [MonitoredAccountResponse.model_validate(a) for a in accounts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats", response_model=SignalStatsResponse)
def signal_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the social signal intelligence dashboard."""
    total_signals = db.query(SocialSignal).count()
    total_clusters = db.query(SignalCluster).count()
    total_voices = db.query(MonitoredAccount).filter(
        MonitoredAccount.is_active == True  # noqa: E712
    ).count()

    # Platform breakdown from signals
    platform_rows = (
        db.query(SocialSignal.platform, func.count(SocialSignal.id))
        .group_by(SocialSignal.platform)
        .all()
    )
    platforms = {row[0]: row[1] for row in platform_rows}

    # Theme breakdown from signals (exclude nulls)
    theme_rows = (
        db.query(SocialSignal.theme, func.count(SocialSignal.id))
        .filter(SocialSignal.theme.isnot(None))
        .group_by(SocialSignal.theme)
        .all()
    )
    themes = {row[0]: row[1] for row in theme_rows}

    return SignalStatsResponse(
        total_signals=total_signals,
        total_clusters=total_clusters,
        total_voices=total_voices,
        platforms=platforms,
        themes=themes,
    )
