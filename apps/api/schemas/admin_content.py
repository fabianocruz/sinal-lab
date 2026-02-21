"""Pydantic schemas for admin content CRUD operations."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContentCreateRequest(BaseModel):
    """Request body for creating a new content piece."""

    title: str = Field(..., min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    body_md: str = Field(..., min_length=1)
    content_type: str = Field("ARTICLE", pattern=r"^(ARTICLE|POST|HOWTO|DATA_REPORT|ANALYSIS|DEEP_DIVE|OPINION|INDEX|COMMUNITY|NEWS)$")
    summary: Optional[str] = None
    meta_description: Optional[str] = Field(None, max_length=320)
    sources: Optional[list[str]] = None


class ContentUpdateRequest(BaseModel):
    """Request body for partially updating a content piece."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    body_md: Optional[str] = Field(None, min_length=1)
    content_type: Optional[str] = Field(None, pattern=r"^(ARTICLE|POST|HOWTO|DATA_REPORT|ANALYSIS|DEEP_DIVE|OPINION|INDEX|COMMUNITY|NEWS)$")
    summary: Optional[str] = None
    meta_description: Optional[str] = Field(None, max_length=320)
    sources: Optional[list[str]] = None


class AdminContentResponse(BaseModel):
    """Response schema for admin content operations."""

    id: UUID
    title: str
    slug: str
    subtitle: Optional[str] = None
    body_md: str = ""
    content_type: str
    agent_name: Optional[str] = None
    review_status: str = "draft"
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sources: Optional[list[str]] = None
    confidence_dq: Optional[float] = None
    meta_description: Optional[str] = None

    class Config:
        from_attributes = True
