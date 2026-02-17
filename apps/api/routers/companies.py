"""Companies router — list and retrieve LATAM tech companies."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import CompanyResponse
from packages.database.models.company import Company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country"),
    status: Optional[str] = Query("active", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List companies with optional filtering."""
    query = db.query(Company)

    if sector:
        query = query.filter(Company.sector == sector)
    if city:
        query = query.filter(Company.city == city)
    if country:
        query = query.filter(Company.country == country)
    if status:
        query = query.filter(Company.status == status)

    companies = (
        query.order_by(desc(Company.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return companies


@router.get("/{slug}", response_model=CompanyResponse)
def get_company_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a specific company by slug."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{slug}' not found")
    return company
