"""Newsletter formatting and delivery for SINTESE agent.

Converts the Markdown newsletter draft into HTML and provides
delivery via Resend (transactional and broadcasts).

Brand template lives in apps.api.services.email_template (single source
of truth for all branded emails).
"""

import logging
from typing import Optional

from apps.api.services.email_template import build_brand_html

logger = logging.getLogger(__name__)


def markdown_to_html(markdown_content: str) -> str:
    """Convert newsletter Markdown to simple HTML.

    Uses basic regex-based conversion for newsletter formatting.
    For production, consider using a proper Markdown library.
    """
    import re

    html = markdown_content

    # Headers
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)

    # Paragraphs (double newline)
    html = re.sub(r"\n\n", r"</p><p>", html)
    html = f"<p>{html}</p>"

    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    return html


def wrap_in_email_template(
    html_body: str,
    edition_title: str,
    unsubscribe_url: Optional[str] = None,
) -> str:
    """Wrap newsletter HTML in the Sinal brand template.

    Delegates to the unified brand template with newsletter_styles=True
    (DM Serif Display h1, h2, blockquotes, horizontal rules).
    """
    return build_brand_html(
        html_body,
        edition_title,
        newsletter_styles=True,
        unsubscribe_url=unsubscribe_url,
    )


def send_via_resend(
    html_content: str,
    subject: str,
    to_email: str,
    from_email: Optional[str] = None,
) -> bool:
    """Send newsletter via Resend API (transactional email to one recipient).

    Requires RESEND_API_KEY environment variable.
    Returns True on success, False on failure.
    """
    from apps.api.config import get_settings

    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email send")
        return False

    from_addr = from_email or settings.resend_from_email

    try:
        import httpx

        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Email sent to %s via Resend", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email via Resend: %s", e)
        return False


def send_broadcast(
    html_content: str,
    subject: str,
) -> bool:
    """Send newsletter to all Audience subscribers via Resend Broadcasts.

    Two-step process:
    1. POST /broadcasts — create broadcast draft
    2. POST /broadcasts/{id}/send — send to audience

    Requires RESEND_API_KEY and RESEND_AUDIENCE_ID.
    Returns True on success, False on failure.
    """
    from apps.api.config import get_settings

    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_audience_id:
        logger.warning(
            "RESEND_API_KEY or RESEND_AUDIENCE_ID not set, skipping broadcast"
        )
        return False

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        import httpx

        # Step 1: Create broadcast
        create_response = httpx.post(
            "https://api.resend.com/broadcasts",
            headers=headers,
            json={
                "audience_id": settings.resend_audience_id,
                "from": settings.resend_from_email,
                "subject": subject,
                "html": html_content,
            },
            timeout=15.0,
        )
        create_response.raise_for_status()
        broadcast_id = create_response.json().get("id")

        if not broadcast_id:
            logger.error("Resend Broadcasts API returned no broadcast ID")
            return False

        # Step 2: Send broadcast
        send_response = httpx.post(
            f"https://api.resend.com/broadcasts/{broadcast_id}/send",
            headers=headers,
            timeout=15.0,
        )
        send_response.raise_for_status()
        logger.info("Newsletter broadcast sent via Resend (ID: %s)", broadcast_id)
        return True

    except Exception as e:
        logger.error("Failed to send broadcast via Resend: %s", e)
        return False
