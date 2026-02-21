"""Email service — branded transactional emails via Resend.

Provides send helpers for transactional emails (welcome, password reset,
etc.) using the Resend REST API. Brand template lives in email_template.py.
"""

import logging
from typing import Optional

import httpx

from apps.api.config import get_settings
from apps.api.services.email_template import build_brand_html

logger = logging.getLogger(__name__)


# Keep backward-compatible alias for existing tests and callers.
def _wrap_in_brand_template(html_body: str, title: str) -> str:
    """Wrap transactional email HTML in the Sinal brand template."""
    return build_brand_html(html_body, title)


def _build_welcome_html(name: Optional[str] = None) -> str:
    """Build the inner HTML for the welcome email.

    All text is in Portuguese with proper accents.
    """
    greeting = f"Ol\u00e1, {name}!" if name else "Ol\u00e1!"

    return f"""
<h1>Bem-vindo ao Sinal</h1>
<p>{greeting}</p>
<p>
    Obrigado por se cadastrar no <strong>Sinal.lab</strong>.
    Voc\u00ea agora faz parte de uma comunidade de fundadores t\u00e9cnicos,
    CTOs e engenheiros s\u00eaniores que acompanham o ecossistema de
    tecnologia da Am\u00e9rica Latina.
</p>
<p>
    Toda semana voc\u00ea receber\u00e1 nosso <strong>briefing semanal</strong>
    com an\u00e1lises sobre rodadas de investimento, tend\u00eancias de
    infraestrutura e movimenta\u00e7\u00f5es do mercado LATAM \u2014 tudo
    filtrado para quem constr\u00f3i.
</p>
<p>
    Voc\u00ea tamb\u00e9m ter\u00e1 acesso a informa\u00e7\u00f5es
    exclusivas sobre os principais pa\u00edses da regi\u00e3o.
</p>
<p>
    Enquanto isso, explore as edi\u00e7\u00f5es anteriores da nossa newsletter:
</p>
<p>
    <a href="https://sinal.ai/newsletter" class="cta-button">
        Ver arquivo da newsletter
    </a>
</p>
<p>
    Se tiver d\u00favidas ou sugest\u00f5es, responda diretamente a este email.
    Lemos todas as mensagens.
</p>
<p>At\u00e9 breve!</p>
"""


def send_welcome_email(email: str, name: Optional[str] = None) -> bool:
    """Send a branded welcome email via the Resend REST API.

    Returns True on success, False on failure. Gracefully degrades
    when RESEND_API_KEY is not configured (returns False without error).
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set, skipping welcome email for %s", email
        )
        return False

    subject = "Bem-vindo ao Sinal \u2014 intelig\u00eancia tech LATAM"
    inner_html = _build_welcome_html(name)
    full_html = _wrap_in_brand_template(inner_html, subject)

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": [email],
                "subject": subject,
                "html": full_html,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Welcome email sent to %s via Resend", email)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Resend API returned %d for welcome email to %s: %s",
            exc.response.status_code,
            email,
            exc.response.text,
        )
        return False
    except Exception as exc:
        logger.error(
            "Failed to send welcome email to %s: %s", email, exc
        )
        return False
