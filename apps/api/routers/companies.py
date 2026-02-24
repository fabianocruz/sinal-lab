"""Companies router — list and retrieve LATAM tech companies.

Response format for GET /api/companies (paginated):
    {
        "items": [CompanyResponse, ...],
        "total": <int>,    # total matching records (before pagination)
        "limit": <int>,    # page size
        "offset": <int>    # current offset
    }

The frontend expects this paginated envelope (same as content router).
Individual endpoint (/{slug}) returns a single CompanyDetailResponse.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import CompanyDetailResponse, CompanyResponse
from packages.database.models.company import Company

router = APIRouter(prefix="/companies", tags=["companies"])


# No response_model — we return a dict envelope {items, total, limit, offset}
# instead of a bare list, so the frontend can handle pagination.
@router.get("")
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country"),
    status: Optional[str] = Query("active", description="Filter by status"),
    search: Optional[str] = Query(None, description="Case-insensitive name search (LIKE)"),
    tags: Optional[str] = Query(None, description="Filter by tag (JSON contains)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List companies with optional filtering and pagination."""
    query = db.query(Company)

    if sector:
        query = query.filter(Company.sector == sector)
    if city:
        query = query.filter(Company.city == city)
    if country:
        query = query.filter(Company.country == country)
    if status:
        query = query.filter(Company.status == status)
    if search:
        query = query.filter(Company.name.ilike(f"%{search}%"))
    if tags:
        query = query.filter(Company.tags.contains([tags]))

    total = query.count()
    companies = (
        query.order_by(desc(Company.source_count), desc(Company.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [CompanyResponse.model_validate(c) for c in companies],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{slug}", response_model=CompanyDetailResponse)
def get_company_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific company by slug."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{slug}' not found")
    return company
