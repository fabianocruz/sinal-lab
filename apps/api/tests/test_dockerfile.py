"""Tests to validate the API Dockerfile configuration.

These tests parse the Dockerfile as text and verify critical properties
(base image, health check, exposed port, required packages) stay correct.
"""

import pathlib
import re

import pytest

DOCKERFILE = pathlib.Path(__file__).resolve().parents[1] / "Dockerfile"


@pytest.fixture
def dockerfile_content():
    """Read the Dockerfile content."""
    assert DOCKERFILE.exists(), f"Dockerfile not found at {DOCKERFILE}"
    return DOCKERFILE.read_text()


# ---------------------------------------------------------------------------
# Base image
# ---------------------------------------------------------------------------


def test_base_image_is_python_312(dockerfile_content):
    """Dockerfile must use Python 3.12 slim as base image."""
    assert re.search(r"FROM\s+python:3\.12-slim", dockerfile_content)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def test_includes_fastapi(dockerfile_content):
    """Dockerfile must install fastapi."""
    assert "fastapi" in dockerfile_content


def test_includes_uvicorn(dockerfile_content):
    """Dockerfile must install uvicorn with standard extras."""
    assert "uvicorn[standard]" in dockerfile_content


def test_includes_bcrypt(dockerfile_content):
    """Dockerfile must install bcrypt for auth."""
    assert "bcrypt" in dockerfile_content


def test_includes_pydantic_settings(dockerfile_content):
    """Dockerfile must install pydantic-settings for config."""
    assert "pydantic-settings" in dockerfile_content


def test_includes_httpx(dockerfile_content):
    """Dockerfile must install httpx for async HTTP."""
    assert "httpx" in dockerfile_content


# ---------------------------------------------------------------------------
# Application layout
# ---------------------------------------------------------------------------


def test_workdir_is_app(dockerfile_content):
    """Working directory must be /app."""
    assert re.search(r"WORKDIR\s+/app", dockerfile_content)


def test_copies_api_code(dockerfile_content):
    """Dockerfile must copy apps/api/ into the image."""
    assert "apps/api/" in dockerfile_content


def test_copies_packages(dockerfile_content):
    """Dockerfile must copy packages/ into the image."""
    assert "packages/" in dockerfile_content


def test_copies_agents(dockerfile_content):
    """Dockerfile must copy apps/agents/ into the image."""
    assert "apps/agents/" in dockerfile_content


def test_pythonpath_set(dockerfile_content):
    """PYTHONPATH must be set to /app for module resolution."""
    assert re.search(r"ENV\s+PYTHONPATH=/app", dockerfile_content)


# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------


def test_exposes_port_8000(dockerfile_content):
    """Dockerfile must expose port 8000."""
    assert re.search(r"EXPOSE\s+8000", dockerfile_content)


def test_port_env_is_8000(dockerfile_content):
    """PORT env var must default to 8000."""
    assert re.search(r"ENV\s+PORT=8000", dockerfile_content)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_healthcheck_exists(dockerfile_content):
    """Dockerfile must define a HEALTHCHECK."""
    assert "HEALTHCHECK" in dockerfile_content


def test_healthcheck_hits_correct_endpoint(dockerfile_content):
    """Health check must hit /health (matches health.router mount)."""
    assert "localhost:8000/health" in dockerfile_content


def test_healthcheck_has_interval(dockerfile_content):
    """Health check must specify an interval."""
    assert "--interval=" in dockerfile_content


def test_healthcheck_has_timeout(dockerfile_content):
    """Health check must specify a timeout."""
    assert "--timeout=" in dockerfile_content


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def test_cmd_runs_uvicorn(dockerfile_content):
    """CMD must start uvicorn with the correct app module."""
    assert "apps.api.main:app" in dockerfile_content


def test_cmd_binds_to_all_interfaces(dockerfile_content):
    """CMD must bind to 0.0.0.0 for container networking."""
    assert "0.0.0.0" in dockerfile_content
