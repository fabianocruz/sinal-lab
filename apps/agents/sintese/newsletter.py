"""Newsletter formatting and delivery for SINTESE agent.

Converts the Markdown newsletter draft into HTML and provides
delivery via Resend (transactional and broadcasts).

Brand template lives in apps.api.services.email_template (single source
of truth for all branded emails).
"""

import logging
import os
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
    """Send newsletter via Resend API (transactional email).

    Requires RESEND_API_KEY environment variable.
    Returns True on success, False on failure.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not set, skipping email send")
        return False

    from_addr = from_email or os.getenv("RESEND_FROM_EMAIL", "newsletter@sinal.ai")

    try:
        import httpx

        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            },
        )
        response.raise_for_status()
        logger.info("Email sent to %s via Resend", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email via Resend: %s", e)
        return False


def send_via_beehiiv(
    html_content: str,
    subject: str,
) -> bool:
    """Publish newsletter via Beehiiv API.

    Requires BEEHIIV_API_KEY and BEEHIIV_PUBLICATION_ID environment variables.
    Returns True on success, False on failure.
    """
    api_key = os.getenv("BEEHIIV_API_KEY")
    pub_id = os.getenv("BEEHIIV_PUBLICATION_ID")

    if not api_key or not pub_id:
        logger.warning("BEEHIIV_API_KEY or BEEHIIV_PUBLICATION_ID not set, skipping")
        return False

    try:
        import httpx

        response = httpx.post(
            f"https://api.beehiiv.com/v2/publications/{pub_id}/posts",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "title": subject,
                "content_html": html_content,
                "status": "draft",
            },
        )
        if response.status_code >= 400:
            logger.error(
                "Beehiiv API error %d: %s", response.status_code, response.text
            )
        response.raise_for_status()
        logger.info("Newsletter published as draft on Beehiiv")
        return True
    except Exception as e:
        logger.error("Failed to publish to Beehiiv: %s", e)
        return False
