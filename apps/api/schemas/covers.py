"""Pydantic schemas for cover image generation endpoint."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CoverGenerateRequest(BaseModel):
    """Request body for cover image generation."""

    headline: str = Field(..., min_length=1, max_length=500)
    lede: str = Field(..., min_length=1, max_length=2000)
    agent: str = Field(..., pattern=r"^(radar|funding|codigo|mercado|sintese)$")
    edition: int = Field(..., ge=1)
    dq_score: Optional[float] = Field(None, ge=0.0, le=5.0)
    variations: int = Field(3, ge=1, le=3)


class CoverImageResponse(BaseModel):
    """A single generated cover image."""

    url: str
    variation: int


class CoverGenerateResponse(BaseModel):
    """Response from cover image generation."""

    images: List[CoverImageResponse]
    prompt_used: str
    agent: str
    errors: List[str] = Field(default_factory=list)
