"""Tests for scripts/cleanup_non_startups.py — non-startup cleanup script.

Verifies the CLI script correctly identifies and deactivates non-startup
entries using the _is_non_startup filter from db_writer.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.agents.index.db_writer import _is_non_startup, cleanup_non_startups


# ---------------------------------------------------------------------------
# _is_non_startup filter
# ---------------------------------------------------------------------------


class TestIsNonStartup:
    """Tests for the _is_non_startup name filter."""

    def test_university_names_detected(self):
        assert _is_non_startup("Universidad de Buenos Aires") is True
        assert _is_non_startup("Universidade Federal do Rio de Janeiro") is True
        assert _is_non_startup("UTN FRBA") is True

    def test_government_names_detected(self):
        assert _is_non_startup("Prefeitura de São Paulo") is True
        assert _is_non_startup("Gobierno de México") is True
        assert _is_non_startup("Ministério da Economia") is True

    def test_school_names_detected(self):
        assert _is_non_startup("Escola Politécnica da USP") is True
        assert _is_non_startup("Instituto Tecnológico de Monterrey") is True

    def test_foundation_names_detected(self):
        assert _is_non_startup("Fundação Getúlio Vargas") is True
        assert _is_non_startup("Fundacion Chile") is True

    def test_startup_names_not_detected(self):
        assert _is_non_startup("Nubank") is False
        assert _is_non_startup("Rappi") is False
        assert _is_non_startup("Mercado Libre") is False
        assert _is_non_startup("Creditas") is False
        assert _is_non_startup("QuintoAndar") is False

    def test_case_insensitive(self):
        assert _is_non_startup("UNIVERSIDAD NACIONAL") is True
        assert _is_non_startup("university of something") is True

    def test_empty_string(self):
        assert _is_non_startup("") is False

    def test_program_names_detected(self):
        assert _is_non_startup("Maestría en Humanidades Digitales") is True
        assert _is_non_startup("Programa de Aceleração") is True


# ---------------------------------------------------------------------------
# cleanup_non_startups function
# ---------------------------------------------------------------------------


class TestCleanupNonStartups:
    """Tests for the cleanup_non_startups DB function."""

    def test_deactivates_non_startups(self):
        """Should set status=inactive for non-startup entries."""
        company1 = MagicMock()
        company1.name = "Universidad de Chile"
        company1.status = "active"

        company2 = MagicMock()
        company2.name = "Nubank"
        company2.status = "active"

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [company1, company2]

        count = cleanup_non_startups(session)

        assert count == 1
        assert company1.status == "inactive"
        assert company2.status == "active"

    def test_returns_zero_when_no_matches(self):
        """Should return 0 when all entries are real startups."""
        company = MagicMock()
        company.name = "Rappi"
        company.status = "active"

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [company]

        count = cleanup_non_startups(session)

        assert count == 0
        assert company.status == "active"

    def test_returns_zero_for_empty_table(self):
        """Should return 0 with no companies in the database."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []

        count = cleanup_non_startups(session)

        assert count == 0

    def test_flushes_session_after_updates(self):
        """Should call session.flush() after making changes."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []

        cleanup_non_startups(session)

        session.flush.assert_called_once()
