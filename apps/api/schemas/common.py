"""Common Pydantic schemas shared across routers."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list[Any]
    total: int
    page: int = 1
    per_page: int = 20


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None


class WaitlistSignup(BaseModel):
    """Request body for waitlist signup."""

    email: str = Field(..., min_length=5, max_length=320)
    name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=255)


class WaitlistResponse(BaseModel):
    """Response for waitlist signup."""

    message: str
    position: Optional[int] = None


class WaitlistCountResponse(BaseModel):
    """Response for waitlist count."""

    count: int


class CompanyResponse(BaseModel):
    """Company response schema (list view)."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Brazil"
    tags: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    founded_date: Optional[date] = None
    team_size: Optional[int] = None
    business_model: Optional[str] = None
    website: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    source_count: int = 1
    status: str = "active"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(CompanyResponse):
    """Company detail response (includes metadata)."""

    metadata_: Optional[dict] = None

    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    """Content piece response schema (list/summary view)."""

    id: UUID
    title: str
    slug: str
    subtitle: Optional[str] = None
    content_type: str
    summary: Optional[str] = None
    agent_name: Optional[str] = None
    confidence_dq: Optional[float] = None
    confidence_ac: Optional[float] = None
    review_status: str = "draft"
    published_at: Optional[datetime] = None
    sources: Optional[list[str]] = None
    meta_description: Optional[str] = None
    author_name: Optional[str] = None
    metadata_: Optional[dict] = None

    class Config:
        from_attributes = True


class ContentDetailResponse(ContentResponse):
    """Content piece detail response (includes body and metadata)."""

    body_md: str = ""
    body_html: Optional[str] = None
    canonical_url: Optional[str] = None

    class Config:
        from_attributes = True


class AgentRunResponse(BaseModel):
    """Agent run response schema."""

    id: UUID
    agent_name: str
    run_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_collected: Optional[int] = None
    items_processed: Optional[int] = None
    avg_confidence: Optional[float] = None
    error_count: int = 0

    class Config:
        from_attributes = True
