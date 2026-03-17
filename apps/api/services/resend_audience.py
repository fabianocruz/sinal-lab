"""Resend Audience service — subscriber management via Resend Contacts API.

Manages newsletter subscribers in a Resend Audience. Contacts are
identified by email (no extra database column needed).

Requires RESEND_API_KEY and RESEND_AUDIENCE_ID environment variables.
"""

import logging
import time
from typing import Optional

import httpx

from apps.api.config import get_settings

logger = logging.getLogger(__name__)

RESEND_CONTACTS_URL = "https://api.resend.com/audiences/{audience_id}/contacts"


def _get_contacts_url() -> Optional[str]:
    """Build the Resend Contacts API URL, or None if not configured."""
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_audience_id:
        return None
    return RESEND_CONTACTS_URL.format(audience_id=settings.resend_audience_id)


def _auth_headers() -> dict:
    """Return Resend API authorization headers."""
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }


def add_contact_to_audience(
    email: str,
    first_name: Optional[str] = None,
) -> bool:
    """Add a contact to the Resend Audience.

    Resend upserts by email — calling this for an existing contact
    updates their name without creating a duplicate.

    Returns True on success, False on failure or missing config.
    """
    url = _get_contacts_url()
    if not url:
        logger.warning(
            "RESEND_API_KEY or RESEND_AUDIENCE_ID not set, skipping audience sync for %s",
            email,
        )
        return False

    payload: dict = {"email": email}
    if first_name:
        payload["first_name"] = first_name

    try:
        response = httpx.post(url, headers=_auth_headers(), json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info("Contact added to Resend Audience: %s", email)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Resend Contacts API returned %d for %s: %s",
            exc.response.status_code,
            email,
            exc.response.text,
        )
        return False
    except Exception as exc:
        logger.error("Failed to add contact %s to audience: %s", email, exc)
        return False


def _find_contact_id(email: str) -> Optional[str]:
    """Look up a Resend contact ID by email address.

    Resend's DELETE endpoint requires the contact ID, not the email.
    This lists all contacts and finds the matching one.
    """
    url = _get_contacts_url()
    if not url:
        return None

    try:
        response = httpx.get(url, headers=_auth_headers(), timeout=15.0)
        response.raise_for_status()
        contacts = response.json().get("data", [])
        for contact in contacts:
            if contact.get("email", "").lower() == email.lower():
                return contact["id"]
    except Exception:
        logger.debug("Failed to look up contact ID for %s", email, exc_info=True)
    return None


def remove_contact_from_audience(email: str) -> bool:
    """Remove a contact from the Resend Audience by email.

    Looks up the contact ID first (Resend DELETE requires ID, not email),
    then deletes. Returns True on success, False on failure or missing config.
    """
    url = _get_contacts_url()
    if not url:
        logger.warning(
            "RESEND_API_KEY or RESEND_AUDIENCE_ID not set, skipping removal for %s",
            email,
        )
        return False

    contact_id = _find_contact_id(email)
    if not contact_id:
        logger.warning("Contact not found in Resend audience: %s", email)
        return False

    try:
        response = httpx.delete(
            f"{url}/{contact_id}",
            headers=_auth_headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Contact removed from Resend Audience: %s", email)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Resend Contacts API returned %d removing %s: %s",
            exc.response.status_code,
            email,
            exc.response.text,
        )
        return False
    except Exception as exc:
        logger.error("Failed to remove contact %s from audience: %s", email, exc)
        return False


def bulk_sync_contacts(
    contacts: list[dict],
    delay: float = 0.6,
) -> dict:
    """Sync a list of contacts to the Resend Audience.

    Each contact dict should have 'email' and optionally 'first_name'.

    Args:
        contacts: List of dicts with 'email' and optional 'first_name'.
        delay: Seconds to wait between API calls (default 0.6s to stay
               under Resend's 2 req/s rate limit).

    Returns {"synced": N, "failed": N, "skipped": bool}.
    """
    url = _get_contacts_url()
    if not url:
        logger.warning("RESEND_API_KEY or RESEND_AUDIENCE_ID not set, skipping bulk sync")
        return {"synced": 0, "failed": 0, "skipped": True}

    synced = 0
    failed = 0

    for i, contact in enumerate(contacts):
        if i > 0:
            time.sleep(delay)

        ok = add_contact_to_audience(
            email=contact["email"],
            first_name=contact.get("first_name"),
        )
        if ok:
            synced += 1
        else:
            failed += 1

    logger.info("Bulk sync complete: %d synced, %d failed", synced, failed)
    return {"synced": synced, "failed": failed, "skipped": False}
