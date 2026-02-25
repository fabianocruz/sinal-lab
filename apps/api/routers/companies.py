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
from sqlalchemy import case, desc, func
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

    # Prioritize companies with richer data using weighted scoring.
    # Essential fields (description, sector, website) get 3x weight;
    # enrichment fields (funding, team, founded) get 2x; extras get 1x.
    # Max score: 9 (essential) + 6 (enrichment) + 1 (extra) = 16.
    _has_text = lambda col: (func.coalesce(func.length(col), 0) > 0)
    data_richness = (
        case((_has_text(Company.description), 3), else_=0)
        + case((_has_text(Company.sector), 3), else_=0)
        + case((_has_text(Company.website), 3), else_=0)
        + case((Company.funding_stage.isnot(None), 2), else_=0)
        + case((Company.team_size.isnot(None), 2), else_=0)
        + case((Company.founded_date.isnot(None), 2), else_=0)
        + case((_has_text(Company.business_model), 1), else_=0)
    )

    companies = (
        query.order_by(desc(data_richness), desc(Company.source_count), desc(Company.created_at))
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
