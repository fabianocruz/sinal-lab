"""Admin router for API key management.

Provides endpoints to create and list API keys. Protected by the
ADMIN_API_SECRET env var (same secret used by other admin endpoints).

Run: pytest apps/api/tests/test_api_keys.py -v
"""

import hashlib
import secrets
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.deps import get_db
from packages.database.models.api_key import ApiKey

router = APIRouter(prefix="/admin/api-keys", tags=["admin-api-keys"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateApiKeyRequest(BaseModel):
    """Request body to create a new API key."""

    email: EmailStr
    name: str


class CreateApiKeyResponse(BaseModel):
    """Response returned exactly once with the plaintext API key."""

    api_key: str
    name: str
    key_prefix: str


class ApiKeyListItem(BaseModel):
    """API key metadata (no plaintext key)."""

    id: UUID
    user_email: str
    key_prefix: str
    name: str
    is_active: bool
    rate_limit: int
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Admin auth helper
# ---------------------------------------------------------------------------


def _require_admin_secret(authorization: str = Header(None)) -> None:
    """Verify the request carries the correct ADMIN_API_SECRET.

    Expects ``Authorization: Bearer <ADMIN_API_SECRET>``.
    """
    settings = get_settings()

    if not settings.admin_api_secret:
        raise HTTPException(status_code=500, detail="ADMIN_API_SECRET nao configurado.")

    if not authorization:
        raise HTTPException(status_code=401, detail="Admin secret ausente.")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Formato de autorizacao invalido.")

    if parts[1] != settings.admin_api_secret:
        raise HTTPException(status_code=401, detail="Admin secret invalido.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=CreateApiKeyResponse, status_code=201)
def create_api_key(
    body: CreateApiKeyRequest,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin_secret),
):
    """Create a new API key for a developer.

    Generates a cryptographically secure key prefixed with ``sk_live_``,
    stores the SHA-256 hash, and returns the plaintext key exactly once.
    """
    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        user_email=body.email,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        is_active=True,
        rate_limit=100,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return CreateApiKeyResponse(
        api_key=raw_key,
        name=api_key.name,
        key_prefix=key_prefix,
    )


@router.get("", response_model=List[ApiKeyListItem])
def list_api_keys(
    email: Optional[str] = Query(None, description="Filter by owner email"),
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin_secret),
):
    """List all API keys (metadata only, no plaintext keys)."""
    query = db.query(ApiKey)
    if email:
        query = query.filter(ApiKey.user_email == email)
    keys = query.order_by(desc(ApiKey.created_at)).all()
    return [ApiKeyListItem.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin_secret),
):
    """Revoke (deactivate) an API key by ID."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key nao encontrada.")
    api_key.is_active = False
    db.commit()
    return None
