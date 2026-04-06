"""Export router — CSV downloads for signals and curated feed data.

Endpoints:
    GET /api/export/signals?format=csv&theme=AI&limit=500
    GET /api/export/feed?format=csv&limit=100

Run: pytest apps/api/tests/test_export.py -v
"""

import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from packages.database.models.curated_feed_item import CuratedFeedItem
from packages.database.models.social_signal import SocialSignal

router = APIRouter(prefix="/export", tags=["export"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SIGNALS_CSV_COLUMNS = [
    "platform",
    "author_handle",
    "author_display_name",
    "text",
    "post_url",
    "published_at",
    "theme",
    "sub_theme",
    "sentiment",
    "authority_score",
    "likes",
    "replies",
    "reposts",
]

FEED_CSV_COLUMNS = [
    "editorial_headline",
    "editorial_context",
    "category",
    "relevance_score",
    "source_platform",
    "source_url",
    "source_author",
    "thumbnail_url",
    "curated_at",
]

MAX_LIMIT = 5000
DEFAULT_SIGNALS_LIMIT = 500
DEFAULT_FEED_LIMIT = 100
TEXT_TRUNCATE_LENGTH = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_filename(prefix: str) -> str:
    """Generate a dated CSV filename, e.g. sinal-signals-2026-04-06.csv."""
    return f"sinal-{prefix}-{date.today().isoformat()}.csv"


def _streaming_csv(rows: list[list[str]], columns: list[str], filename: str) -> StreamingResponse:
    """Build a StreamingResponse from a list of rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    writer.writerows(rows)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _format_value(value: object) -> str:
    """Convert a value to a CSV-safe string."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _extract_metric(metrics: Optional[dict], key: str) -> str:
    """Safely extract a metric from the JSON metrics dict."""
    if not metrics:
        return ""
    val = metrics.get(key)
    if val is None:
        return ""
    return str(val)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/signals")
def export_signals(
    format: str = Query("csv", description="Export format (csv)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    theme: Optional[str] = Query(None, description="Filter by theme"),
    sub_theme: Optional[str] = Query(None, description="Filter by sub-theme"),
    search: Optional[str] = Query(None, description="Text search (LIKE)"),
    limit: int = Query(DEFAULT_SIGNALS_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export social signals as CSV.

    Accepts the same filters as GET /api/signals. Returns a downloadable CSV
    file with a Content-Disposition header.
    """
    query = db.query(SocialSignal)

    if platform:
        query = query.filter(SocialSignal.platform == platform)
    if theme:
        query = query.filter(SocialSignal.theme == theme)
    if sub_theme:
        query = query.filter(SocialSignal.sub_theme == sub_theme)
    if search:
        query = query.filter(SocialSignal.text.ilike(f"%{search}%"))

    signals = (
        query.order_by(desc(SocialSignal.published_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    rows: list[list[str]] = []
    for s in signals:
        text = (s.text or "")[:TEXT_TRUNCATE_LENGTH]
        rows.append([
            _format_value(s.platform),
            _format_value(s.author_handle),
            _format_value(s.author_display_name),
            text,
            _format_value(s.post_url),
            _format_value(s.published_at),
            _format_value(s.theme),
            _format_value(s.sub_theme),
            _format_value(s.sentiment),
            _format_value(s.authority_score),
            _extract_metric(s.metrics, "likes"),
            _extract_metric(s.metrics, "replies"),
            _extract_metric(s.metrics, "reposts"),
        ])

    filename = _csv_filename("signals")
    return _streaming_csv(rows, SIGNALS_CSV_COLUMNS, filename)


@router.get("/feed")
def export_feed(
    format: str = Query("csv", description="Export format (csv)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    theme: Optional[str] = Query(None, description="Alias for category"),
    limit: int = Query(DEFAULT_FEED_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export curated feed items as CSV.

    Accepts the same filters as GET /api/signals/feed. Returns a downloadable
    CSV file with a Content-Disposition header.
    """
    filter_category = category or theme
    query = db.query(CuratedFeedItem)

    if filter_category:
        query = query.filter(CuratedFeedItem.category == filter_category)

    items = (
        query.order_by(desc(CuratedFeedItem.relevance_score))
        .offset(offset)
        .limit(limit)
        .all()
    )

    rows: list[list[str]] = []
    for item in items:
        rows.append([
            _format_value(item.editorial_headline),
            _format_value(item.editorial_context),
            _format_value(item.category),
            _format_value(item.relevance_score),
            _format_value(item.source_platform),
            _format_value(item.source_url),
            _format_value(item.source_author),
            _format_value(item.thumbnail_url),
            _format_value(item.curated_at),
        ])

    filename = _csv_filename("feed")
    return _streaming_csv(rows, FEED_CSV_COLUMNS, filename)
