"""Pydantic schemas for developer API access requests."""

from pydantic import BaseModel, Field


class ApiAccessRequest(BaseModel):
    """Request body for API access request form."""

    name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=320)
    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=100)
    use_case: str = Field(..., min_length=10, max_length=2000)


class ApiAccessResponse(BaseModel):
    """Response for API access request submission."""

    message: str
