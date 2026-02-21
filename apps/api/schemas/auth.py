"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=255)


class VerifyRequest(BaseModel):
    """Request body for credential verification (called by NextAuth)."""

    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)


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
