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
from collections import defaultdict

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.agents.social_signals.config import (
    CLUSTER_NAME_BLOCKLIST,
    CLUSTER_NAME_BLOCKLIST_RE,
    MIN_CLUSTER_COMPOSITE_SCORE,
)
from packages.database.models.curated_feed_item import CuratedFeedItem
from packages.database.models.monitored_account import MonitoredAccount
from packages.database.models.signal_cluster import SignalCluster
from packages.database.models.social_signal import SocialSignal
from packages.database.models.watchlist_item import WatchlistItem
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


class RecentSignalBrief(BaseModel):
    """Compact signal summary attached to a voice card."""

    platform: str
    text: Optional[str] = None
    post_url: str
    published_at: Optional[datetime] = None
    metrics: Optional[Dict[str, Any]] = None

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
    recent_signals: List[RecentSignalBrief] = []

    class Config:
        from_attributes = True


class CuratedFeedItemResponse(BaseModel):
    """Curated feed item response schema.

    Field names are aligned with the frontend CuratedFeedItem interface.
    DB column names (source_*) are mapped to frontend names (platform, original_*, author_*).
    """

    id: UUID
    editorial_headline: str
    editorial_context: Optional[str] = None
    relevance_score: int = 0
    category: str
    # Mapped fields — frontend expects these names
    original_text: Optional[str] = None
    original_url: Optional[str] = None
    platform: Optional[str] = None
    author_handle: Optional[str] = None
    author_display_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_embed: Optional[Dict[str, Any]] = None
    theme: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    curated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_db(cls, item: Any) -> "CuratedFeedItemResponse":
        """Build response from a CuratedFeedItem DB model, mapping field names."""
        video_embed = None
        if item.embed_type and item.embed_url:
            thumbnail = None
            if item.embed_type == "youtube":
                # Extract video ID from embed URL
                embed_url = item.embed_url or ""
                vid = embed_url.rsplit("/", 1)[-1] if "/" in embed_url else ""
                if vid:
                    thumbnail = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
            video_embed = {
                "platform": item.embed_type,
                "embed_url": item.embed_url,
                "thumbnail": thumbnail,
            }

        return cls(
            id=item.id,
            editorial_headline=item.editorial_headline,
            editorial_context=item.editorial_context,
            relevance_score=item.relevance_score,
            category=item.category,
            original_text=item.source_text or "",
            original_url=item.source_url or "",
            platform=item.source_platform or "",
            author_handle=item.source_author or "",
            author_display_name=item.source_author or "",
            thumbnail_url=item.thumbnail_url,
            video_embed=video_embed,
            theme=item.category,  # Use category as theme for frontend
            metrics=None,
            curated_at=item.curated_at,
        )


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
    min_score: Optional[float] = Query(
        MIN_CLUSTER_COMPOSITE_SCORE,
        ge=0.0,
        le=1.0,
        description="Minimum composite score (0-1). Pass 0 to include all clusters.",
    ),
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
    if min_score and min_score > 0:
        query = query.filter(SignalCluster.composite_score >= min_score)

    # Exclude clusters with generic/noise names.
    # Fetch all matching rows and filter in Python with pre-compiled regex.
    # This avoids N individual SQL NOT ILIKE clauses and works with both
    # PostgreSQL and SQLite (tests).
    all_matching = (
        query.order_by(desc(SignalCluster.composite_score))
        .all()
    )
    filtered = [c for c in all_matching if not CLUSTER_NAME_BLOCKLIST_RE.search(c.name or "")]
    total = len(filtered)
    clusters = filtered[offset : offset + limit]

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
    # Block clusters matching name blocklist (same filter as list endpoint)
    if CLUSTER_NAME_BLOCKLIST_RE.search(cluster.name or ""):
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
    sort_by: str = Query(
        "recent_activity",
        description="Sort strategy: 'recent_activity' (default, activity in last 7d "
        "then authority) or 'authority' (historical only).",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List monitored accounts (voices) with recent signals.

    Each voice is enriched with up to 3 recent signals. Matching strategy:
        1. Exact author_handle match (same handle on both sides)
        2. Sector-tag fallback: find signals whose theme matches any of
           the voice's sector_tags (e.g. voice with tags ["fintech", "ai"]
           matches signals with theme "AI" or "Fintech")

    This solves the handle mismatch problem where monitored accounts come
    from Crunchbase (handle="sam-altman") but signals come from Twitter
    (author_handle="sama").
    """
    query = db.query(MonitoredAccount)

    if platform:
        query = query.filter(MonitoredAccount.platform == platform)
    if account_type:
        query = query.filter(MonitoredAccount.account_type == account_type)
    if is_active is not None:
        query = query.filter(MonitoredAccount.is_active == is_active)

    total = query.count()

    if sort_by == "authority":
        # Historical authority only (legacy behaviour).
        accounts = (
            query.order_by(desc(MonitoredAccount.authority_score))
            .offset(offset)
            .limit(limit)
            .all()
        )
        signals_by_handle = _batch_fetch_signals_for_voices(db, accounts)
    else:
        # Default: rank by recent activity (7d) then authority as tiebreaker.
        # Pull a wider slice, join with activity counts, then slice.
        all_accounts = (
            query.order_by(desc(MonitoredAccount.authority_score))
            .limit(500)  # cap for performance; 500 covers typical leaderboard depth
            .all()
        )
        signals_by_handle = _batch_fetch_signals_for_voices(db, all_accounts)
        all_accounts.sort(
            key=lambda a: (
                len(signals_by_handle.get(a.handle, [])),
                a.authority_score or 0.0,
            ),
            reverse=True,
        )
        accounts = all_accounts[offset : offset + limit]

    items: List[MonitoredAccountResponse] = []
    for account in accounts:
        voice_data = MonitoredAccountResponse.model_validate(account)
        matched_signals = signals_by_handle.get(account.handle, [])
        voice_data.recent_signals = [
            RecentSignalBrief(
                platform=sig.platform or "unknown",
                text=(sig.text or "")[:200],
                post_url=sig.post_url or "",
                published_at=sig.published_at,
                metrics=sig.metrics if isinstance(sig.metrics, dict) else None,
            )
            for sig in matched_signals[:3]
        ]
        items.append(voice_data)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _batch_fetch_signals_for_voices(
    db: Session,
    accounts: List[MonitoredAccount],
    per_voice_limit: int = 3,
) -> Dict[str, List[Any]]:
    """Batch-fetch recent signals for multiple monitored accounts.

    Returns a dict mapping account handle -> list of SocialSignal rows
    (already sorted by published_at DESC, at most ``per_voice_limit`` each).

    Matching strategy (applied in priority order):
        1. Exact author_handle match
        2. display_name containment (cross-platform)
        3. Sector-tag -> theme fallback

    Uses at most 3 DB queries total (one per strategy) instead of
    N queries per account.
    """
    if not accounts:
        return {}

    result: Dict[str, List[Any]] = {}
    # Upper bound on signals to fetch per strategy. With 100 accounts and
    # 3 signals each we need at most 300 rows, but some handles will share
    # signals so we fetch a generous batch.
    batch_limit = len(accounts) * per_voice_limit * 2

    # --- Strategy 1: exact handle match -----------------------------------
    all_handles = [a.handle for a in accounts]
    handle_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.author_handle.in_(all_handles))
        .order_by(desc(SocialSignal.published_at))
        .limit(batch_limit)
        .all()
    )

    by_handle: Dict[str, List[Any]] = defaultdict(list)
    for sig in handle_signals:
        by_handle[sig.author_handle].append(sig)

    matched_handles = set()
    for account in accounts:
        sigs = by_handle.get(account.handle, [])
        if sigs:
            result[account.handle] = sigs[:per_voice_limit]
            matched_handles.add(account.handle)

    # --- Strategy 2: display_name containment (cross-platform) ------------
    unmatched_by_name = [
        a for a in accounts
        if a.handle not in matched_handles
        and (a.display_name or "").strip()
        and len((a.display_name or "").strip()) > 3
    ]
    if unmatched_by_name:
        name_conditions = [
            SocialSignal.author_display_name.ilike(f"%{a.display_name.strip()}%")
            for a in unmatched_by_name
        ]
        name_signals = (
            db.query(SocialSignal)
            .filter(or_(*name_conditions))
            .order_by(desc(SocialSignal.published_at))
            .limit(batch_limit)
            .all()
        )

        # Group results: for each unmatched account check which signals match
        for account in unmatched_by_name:
            display = account.display_name.strip().lower()
            matching = [
                s for s in name_signals
                if s.author_display_name
                and display in s.author_display_name.lower()
            ]
            if matching:
                result[account.handle] = matching[:per_voice_limit]
                matched_handles.add(account.handle)

    # --- Strategy 3: sector_tags -> theme fallback ------------------------
    tag_to_theme = {
        "fintech": "Fintech", "ai": "AI", "banking": "AI in Banking",
        "healthtech": "HealthTech", "devtools": "DevTools", "crypto": "Fintech",
        "saas": "AI", "investor": "Funding", "vc": "VC",
        "exec": "AI", "executive": "AI", "founder": "Startup Ops",
        "thought_leader": "AI", "company": "Fintech",
    }
    # Collect all needed themes across remaining unmatched accounts
    unmatched_tag_accounts = [
        a for a in accounts if a.handle not in matched_handles
    ]
    all_themes: set = set()
    account_themes: Dict[str, set] = {}
    for account in unmatched_tag_accounts:
        themes_for_account: set = set()
        for tag in (account.sector_tags or []):
            mapped = tag_to_theme.get(tag.lower())
            if mapped:
                themes_for_account.add(mapped)
                all_themes.add(mapped)
        account_themes[account.handle] = themes_for_account

    if all_themes:
        theme_signals = (
            db.query(SocialSignal)
            .filter(SocialSignal.theme.in_(list(all_themes)))
            .order_by(desc(SocialSignal.published_at))
            .limit(batch_limit)
            .all()
        )

        # Group by theme for fast lookup
        by_theme: Dict[str, List[Any]] = defaultdict(list)
        for sig in theme_signals:
            if sig.theme:
                by_theme[sig.theme].append(sig)

        for account in unmatched_tag_accounts:
            themes = account_themes.get(account.handle, set())
            if not themes:
                continue
            matching = []
            seen_ids: set = set()
            for theme in themes:
                for sig in by_theme.get(theme, []):
                    if sig.id not in seen_ids:
                        matching.append(sig)
                        seen_ids.add(sig.id)
                    if len(matching) >= per_voice_limit:
                        break
                if len(matching) >= per_voice_limit:
                    break
            if matching:
                result[account.handle] = matching[:per_voice_limit]

    return result


def _find_recent_signals_for_voice(
    db: Session,
    account: MonitoredAccount,
    signal_limit: int = 3,
) -> list:
    """Find recent signals relevant to a monitored account.

    Strategy:
        1. Exact author_handle match
        2. Sector-tag fallback (theme ILIKE any tag)

    Args:
        db: Database session.
        account: The monitored account to match against.
        signal_limit: Max signals to return per voice.

    Returns:
        List of SocialSignal records (may be empty).
    """
    # Strategy 1: exact handle match (same platform)
    by_handle = (
        db.query(SocialSignal)
        .filter(SocialSignal.author_handle == account.handle)
        .order_by(desc(SocialSignal.published_at))
        .limit(signal_limit)
        .all()
    )
    if by_handle:
        return by_handle

    # Strategy 2: display_name containment (cross-platform)
    display_name = (account.display_name or "").strip()
    if display_name and len(display_name) > 3:
        by_name = (
            db.query(SocialSignal)
            .filter(SocialSignal.author_display_name.ilike(f"%{display_name}%"))
            .order_by(desc(SocialSignal.published_at))
            .limit(signal_limit)
            .all()
        )
        if by_name:
            return by_name

    # Strategy 3: match by sector_tags -> signal theme
    # Map common account tags to signal themes
    tag_to_theme = {
        "fintech": "Fintech", "ai": "AI", "banking": "AI in Banking",
        "healthtech": "HealthTech", "devtools": "DevTools", "crypto": "Fintech",
        "saas": "AI", "investor": "Funding", "vc": "VC",
        "exec": "AI", "executive": "AI", "founder": "Startup Ops",
        "thought_leader": "AI", "company": "Fintech",
    }
    tags = account.sector_tags or []
    theme_conditions = []
    for tag in tags:
        mapped = tag_to_theme.get(tag.lower())
        if mapped:
            theme_conditions.append(SocialSignal.theme == mapped)

    if not theme_conditions:
        return []

    return (
        db.query(SocialSignal)
        .filter(or_(*theme_conditions))
        .order_by(desc(SocialSignal.published_at))
        .limit(signal_limit)
        .all()
    )


@router.get("/feed")
def list_curated_feed(
    category: Optional[str] = Query(None, description="Filter by category (AI, Fintech, Banking, Startup)"),
    theme: Optional[str] = Query(None, description="Alias for category (used by frontend)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List curated feed items with optional category filtering and pagination.

    Returns editorially curated signals with headlines, context, thumbnails,
    and embed information. Items are ordered by curated_at descending so the
    newest curation appears first ("CURADO EM TEMPO REAL"). curated_at can
    be NULL on legacy rows; fall back to created_at, then relevance_score
    as a final tiebreaker.
    Accepts both `category` and `theme` query params (theme is an alias).
    """
    filter_category = category or theme
    query = db.query(CuratedFeedItem)

    if filter_category:
        query = query.filter(CuratedFeedItem.category == filter_category)

    total = query.count()
    items = (
        query.order_by(
            desc(func.coalesce(CuratedFeedItem.curated_at, CuratedFeedItem.created_at)),
            desc(CuratedFeedItem.relevance_score),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [CuratedFeedItemResponse.from_db(i) for i in items],
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


# ---------------------------------------------------------------------------
# Watchlist — user-specific bookmarks for clusters and voices
# ---------------------------------------------------------------------------


class WatchlistItemResponse(BaseModel):
    """Watchlist item response schema."""

    id: UUID
    user_email: str
    item_type: str
    item_slug: str
    item_name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WatchlistItemCreate(BaseModel):
    """Request body to add an item to the watchlist."""

    email: str
    item_type: str  # "cluster" or "voice"
    item_slug: str
    item_name: str


@router.get("/watchlist")
def list_watchlist(
    email: str = Query(..., description="User email to filter watchlist"),
    item_type: Optional[str] = Query(None, description="Filter by item type (cluster, voice)"),
    db: Session = Depends(get_db),
):
    """List watchlist items for a user, optionally filtered by item_type."""
    query = db.query(WatchlistItem).filter(WatchlistItem.user_email == email)

    if item_type:
        query = query.filter(WatchlistItem.item_type == item_type)

    items = query.order_by(desc(WatchlistItem.created_at)).all()
    return {
        "items": [WatchlistItemResponse.model_validate(i) for i in items],
        "total": len(items),
    }


@router.post("/watchlist", status_code=201)
def add_to_watchlist(
    body: WatchlistItemCreate,
    db: Session = Depends(get_db),
):
    """Add an item to a user's watchlist.

    Returns 409 if the item already exists (unique constraint on email + type + slug).
    """
    # Check for existing duplicate
    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_email == body.email,
            WatchlistItem.item_type == body.item_type,
            WatchlistItem.item_slug == body.item_slug,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Item already in watchlist")

    item = WatchlistItem(
        user_email=body.email,
        item_type=body.item_type,
        item_slug=body.item_slug,
        item_name=body.item_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistItemResponse.model_validate(item)


@router.delete("/watchlist/{item_id}", status_code=204)
def remove_from_watchlist(
    item_id: UUID,
    db: Session = Depends(get_db),
):
    """Remove an item from a user's watchlist by item ID."""
    item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(item)
    db.commit()
    return None
