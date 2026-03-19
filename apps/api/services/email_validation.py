"""Email validation service with disposable/test domain blocking.

Centralizes email format and domain validation for all signup flows
(waitlist, auth register, developer access). Prevents fake/test emails
from entering the database and Resend audience.

Domain blocking is disabled when API_ENV=test (set automatically by
conftest.py) so that existing test fixtures using @example.com work.
"""

import os
import re
from typing import Optional

# RFC-lite format check: local@domain.tld
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Domains that should never be accepted in production signups.
# Covers common test, disposable, and placeholder domains.
BLOCKED_DOMAINS: frozenset[str] = frozenset({
    # RFC 2606 reserved domains
    "example.com",
    "example.net",
    "example.org",
    "test.com",
    "test.net",
    "test.org",
    "localhost",
    "invalid",
    # Common disposable email services
    "mailinator.com",
    "guerrillamail.com",
    "guerrillamail.de",
    "grr.la",
    "sharklasers.com",
    "guerrillamailblock.com",
    "yopmail.com",
    "yopmail.fr",
    "tempmail.com",
    "temp-mail.org",
    "throwaway.email",
    "dispostable.com",
    "maildrop.cc",
    "trashmail.com",
    "trashmail.me",
    "10minutemail.com",
    "minutemail.com",
    "tempail.com",
    "mohmal.com",
    "getnada.com",
    "emailondeck.com",
    "mailnesia.com",
    "tempr.email",
    "fake.com",
    "fakeinbox.com",
    # Generic/placeholder business domains (common in spam submissions)
    "empresa.com",
    "company.com",
    "startup.com",
    "negocio.com",
    "business.com",
    "corp.com",
    "acme.com",
    "contato.com",
    "info.com",
    "noreply.com",
})


def validate_email(email: str) -> Optional[str]:
    """Validate email format and domain.

    Returns None if valid, or an error message string if invalid.
    Domain blocking is skipped when API_ENV=test.
    """
    if not EMAIL_REGEX.match(email):
        return "Email inválido."

    # Skip domain blocking in test environment
    if os.environ.get("API_ENV") == "test":
        return None

    domain = email.split("@")[-1].lower()

    if domain in BLOCKED_DOMAINS:
        return "Domínio de email não aceito. Use um email profissional ou pessoal."

    return None
