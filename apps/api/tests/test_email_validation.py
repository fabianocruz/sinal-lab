"""Tests for the email validation service.

Covers format validation, domain blocking in production mode, and the
test-environment bypass (API_ENV=test) that allows @example.com fixtures
to work in the rest of the test suite.

Note: conftest.py sets API_ENV=test globally. Tests that need production
behaviour (domain blocking active) must temporarily unset that variable
via monkeypatch.
"""

import os
from typing import Optional

import pytest

from apps.api.services.email_validation import (
    BLOCKED_DOMAINS,
    EMAIL_REGEX,
    validate_email,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prod_validate(monkeypatch: pytest.MonkeyPatch, email: str) -> Optional[str]:
    """Run validate_email with domain blocking active (API_ENV unset)."""
    monkeypatch.delenv("API_ENV", raising=False)
    return validate_email(email)


# ---------------------------------------------------------------------------
# EMAIL_REGEX — direct constant checks
# ---------------------------------------------------------------------------


class TestEmailRegex:
    def test_email_regex_matches_standard_address(self) -> None:
        assert EMAIL_REGEX.match("user@gmail.com") is not None

    def test_email_regex_matches_subdomain_address(self) -> None:
        assert EMAIL_REGEX.match("user@mail.company.io") is not None

    def test_email_regex_matches_plus_addressing(self) -> None:
        assert EMAIL_REGEX.match("user+tag@domain.com") is not None

    def test_email_regex_rejects_missing_at_sign(self) -> None:
        assert EMAIL_REGEX.match("userdomain.com") is None

    def test_email_regex_rejects_missing_tld(self) -> None:
        assert EMAIL_REGEX.match("user@domain") is None

    def test_email_regex_rejects_space_in_local_part(self) -> None:
        assert EMAIL_REGEX.match("us er@domain.com") is None

    def test_email_regex_rejects_space_in_domain(self) -> None:
        assert EMAIL_REGEX.match("user@do main.com") is None

    def test_email_regex_rejects_empty_string(self) -> None:
        assert EMAIL_REGEX.match("") is None


# ---------------------------------------------------------------------------
# BLOCKED_DOMAINS — constant integrity checks
# ---------------------------------------------------------------------------


class TestBlockedDomainsConstant:
    def test_blocked_domains_is_frozenset(self) -> None:
        assert isinstance(BLOCKED_DOMAINS, frozenset)

    def test_blocked_domains_contains_example_com(self) -> None:
        assert "example.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_test_com(self) -> None:
        assert "test.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_mailinator(self) -> None:
        assert "mailinator.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_yopmail(self) -> None:
        assert "yopmail.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_empresa_com(self) -> None:
        assert "empresa.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_company_com(self) -> None:
        assert "company.com" in BLOCKED_DOMAINS

    def test_blocked_domains_contains_startup_com(self) -> None:
        assert "startup.com" in BLOCKED_DOMAINS

    def test_blocked_domains_stored_as_lowercase(self) -> None:
        for domain in BLOCKED_DOMAINS:
            assert domain == domain.lower(), f"Domain not lowercase: {domain}"


# ---------------------------------------------------------------------------
# validate_email — happy path (test mode, format checks only)
# ---------------------------------------------------------------------------


class TestValidateEmailHappyPath:
    """These run with API_ENV=test (set by conftest.py), so only format is checked."""

    def test_validate_email_gmail_returns_none(self) -> None:
        assert validate_email("user@gmail.com") is None

    def test_validate_email_corporate_domain_returns_none(self) -> None:
        assert validate_email("fabiano@company.com.br") is None

    def test_validate_email_subdomain_returns_none(self) -> None:
        assert validate_email("dev@mail.startup.io") is None

    def test_validate_email_plus_addressing_returns_none(self) -> None:
        assert validate_email("user+newsletter@gmail.com") is None

    def test_validate_email_numeric_local_part_returns_none(self) -> None:
        assert validate_email("123@domain.org") is None

    def test_validate_email_example_com_allowed_in_test_mode(self) -> None:
        # example.com is blocked in production but passes in test mode
        assert validate_email("fixture@example.com") is None

    def test_validate_email_test_com_allowed_in_test_mode(self) -> None:
        assert validate_email("fixture@test.com") is None

    def test_validate_email_mailinator_allowed_in_test_mode(self) -> None:
        assert validate_email("fixture@mailinator.com") is None


# ---------------------------------------------------------------------------
# validate_email — invalid format
# ---------------------------------------------------------------------------


class TestValidateEmailInvalidFormat:
    def test_validate_email_no_at_sign_returns_error(self) -> None:
        result = validate_email("userdomain.com")
        assert result is not None
        assert "inválido" in result.lower() or "invalid" in result.lower()

    def test_validate_email_no_domain_returns_error(self) -> None:
        result = validate_email("user@")
        assert result is not None

    def test_validate_email_no_tld_returns_error(self) -> None:
        result = validate_email("user@domain")
        assert result is not None

    def test_validate_email_space_in_address_returns_error(self) -> None:
        result = validate_email("us er@domain.com")
        assert result is not None

    def test_validate_email_empty_string_returns_error(self) -> None:
        result = validate_email("")
        assert result is not None

    def test_validate_email_only_at_sign_returns_error(self) -> None:
        result = validate_email("@")
        assert result is not None

    def test_validate_email_double_at_sign_returns_error(self) -> None:
        # "a@@b.com" has two @ chars — the regex forbids @ in local part
        result = validate_email("a@@b.com")
        assert result is not None

    def test_validate_email_unicode_space_returns_error(self) -> None:
        # Non-breaking space (U+00A0) is not \s but EMAIL_REGEX uses [^\s@]
        # Regular space should be rejected
        result = validate_email("user @domain.com")
        assert result is not None

    def test_validate_email_returns_string_not_exception(self) -> None:
        # Ensure the function never raises — always returns str or None
        for bad in ["", "@", "@@", "no-at-sign", "   "]:
            result = validate_email(bad)
            assert isinstance(result, str), f"Expected str for input {bad!r}, got {result!r}"


# ---------------------------------------------------------------------------
# validate_email — domain blocking (production mode)
# ---------------------------------------------------------------------------


class TestValidateEmailDomainBlockingProductionMode:
    """Each test uses monkeypatch to unset API_ENV, activating domain blocking."""

    def test_validate_email_example_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = _prod_validate(monkeypatch, "user@example.com")
        assert result is not None
        assert "domínio" in result.lower() or "domain" in result.lower() or "aceito" in result.lower()

    def test_validate_email_test_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@test.com") is not None

    def test_validate_email_mailinator_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "signup@mailinator.com") is not None

    def test_validate_email_yopmail_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "anon@yopmail.com") is not None

    def test_validate_email_guerrillamail_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "anon@guerrillamail.com") is not None

    def test_validate_email_tempmail_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "anon@tempmail.com") is not None

    def test_validate_email_fake_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@fake.com") is not None

    def test_validate_email_trashmail_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@trashmail.com") is not None

    def test_validate_email_10minutemail_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@10minutemail.com") is not None

    def test_validate_email_example_net_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@example.net") is not None

    def test_validate_email_example_org_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@example.org") is not None

    def test_validate_email_empresa_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "ana@empresa.com") is not None

    def test_validate_email_company_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@company.com") is not None

    def test_validate_email_startup_com_blocked_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@startup.com") is not None

    def test_validate_email_valid_address_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "founder@startup.com.br") is None

    def test_validate_email_gmail_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@gmail.com") is None


# ---------------------------------------------------------------------------
# validate_email — case-insensitive domain blocking
# ---------------------------------------------------------------------------


class TestValidateEmailCaseInsensitiveDomainBlocking:
    def test_validate_email_uppercase_example_com_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@EXAMPLE.COM") is not None

    def test_validate_email_mixed_case_example_com_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@Example.Com") is not None

    def test_validate_email_uppercase_mailinator_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@MAILINATOR.COM") is not None

    def test_validate_email_mixed_case_yopmail_blocked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@YoPmAiL.CoM") is not None

    def test_validate_email_uppercase_local_part_is_irrelevant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Local part case must not affect domain check
        assert _prod_validate(monkeypatch, "USER@example.com") is not None


# ---------------------------------------------------------------------------
# validate_email — similar but non-blocked domains
# ---------------------------------------------------------------------------


class TestValidateEmailSimilarNonBlockedDomains:
    """Domains that look like blocked ones but are legitimate."""

    def test_validate_email_testcompany_com_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "dev@testcompany.com") is None

    def test_validate_email_examples_com_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@examples.com") is None

    def test_validate_email_mytest_com_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@mytest.com") is None

    def test_validate_email_notmailinator_com_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _prod_validate(monkeypatch, "user@notmailinator.com") is None

    def test_validate_email_subfakemain_com_passes_in_prod(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # "fake" in subdomain is NOT the blocked domain "fake.com"
        assert _prod_validate(monkeypatch, "user@not-fake.com") is None

    def test_validate_email_yopmail_subfolder_domain_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # yopmail.company.com is not yopmail.com
        assert _prod_validate(monkeypatch, "user@yopmail.company.com") is None


# ---------------------------------------------------------------------------
# validate_email — test mode bypass
# ---------------------------------------------------------------------------


class TestValidateEmailTestModeBypasses:
    """Verify that API_ENV=test suppresses domain blocking entirely."""

    def test_validate_email_all_blocked_domains_pass_in_test_mode(self) -> None:
        # API_ENV=test is set by conftest.py — no monkeypatch needed
        for domain in sorted(BLOCKED_DOMAINS):
            # Skip bare TLDs / non-addressable entries like "localhost", "invalid"
            if "." not in domain:
                result = validate_email(f"user@{domain}")
                # Format check: user@localhost has no TLD — expect error
                assert result is not None, (
                    f"Expected format error for user@{domain}"
                )
            else:
                result = validate_email(f"fixture@{domain}")
                assert result is None, (
                    f"Expected None in test mode for fixture@{domain}, got {result!r}"
                )

    def test_validate_email_api_env_set_to_test_confirms_bypass(self) -> None:
        assert os.environ.get("API_ENV") == "test"
        # Blocked domain must pass format but be allowed through
        assert validate_email("x@mailinator.com") is None

    def test_validate_email_api_env_other_value_enables_blocking(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("API_ENV", "production")
        assert validate_email("x@mailinator.com") is not None

    def test_validate_email_api_env_unset_enables_blocking(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("API_ENV", raising=False)
        assert validate_email("x@example.com") is not None
