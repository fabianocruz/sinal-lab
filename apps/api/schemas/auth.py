"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UTMData(BaseModel):
    """Acquisition attribution captured client-side and forwarded at signup."""

    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=200)
    referrer: Optional[str] = Field(None, max_length=500)
    landing_path: Optional[str] = Field(None, max_length=500)


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=255)
    utm: Optional[UTMData] = None


class VerifyRequest(BaseModel):
    """Request body for credential verification (called by NextAuth)."""

    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)


class OAuthSyncRequest(BaseModel):
    """Request body for syncing an OAuth provider user to the database.

    Called by NextAuth's signIn callback when a user authenticates via
    Google OAuth. Creates or updates the user in PostgreSQL.
    """

    email: str = Field(..., min_length=5, max_length=320)
    name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    provider: str = Field(..., max_length=50)  # "google"
    provider_id: str = Field(..., max_length=255)  # Google sub ID
    utm: Optional[UTMData] = None


class UserResponse(BaseModel):
    """Public user profile response."""

    id: UUID
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    status: str = "waitlist"
    is_founding_member: bool = False
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True
