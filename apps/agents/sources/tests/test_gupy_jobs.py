"""Tests for Gupy job board source module.

Tests GupyJobListing dataclass, extract_tech_stack and infer_seniority
helpers, and the fetch_gupy_jobs function that collects tech job listings
from Gupy company career pages.
"""

from unittest.mock import MagicMock

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.dedup import compute_content_hash
from apps.agents.sources.gupy_jobs import (
    GupyJobListing,
    extract_tech_stack,
    fetch_gupy_jobs,
    infer_seniority,
)
from apps.agents.sources.verification import SourceAuthority, VerificationLevel

# ---------------------------------------------------------------------------
# Sample mock data
# ---------------------------------------------------------------------------

SAMPLE_GUPY_RESPONSE = {
    "data": [
        {
            "id": 12345,
            "name": "Senior Software Engineer - Backend",
            "description": "<p>Experience with Python, FastAPI, Docker and PostgreSQL</p>",
            "departmentName": "Engineering",
            "city": "São Paulo",
            "workplaceType": "remote",
            "publishedDate": "2026-02-01T10:00:00Z",
        },
        {
            "id": 12346,
            "name": "Desenvolvedor Pleno Frontend",
            "description": "React, TypeScript, and Node.js experience required",
            "departmentName": "Engineering",
            "city": "Remote",
            "workplaceType": "remote",
            "publishedDate": "2026-02-05T14:00:00Z",
        },
    ]
}

SAMPLE_GUPY_RESPONSE_SECOND = {
    "data": [
        {
            "id": 99999,
            "name": "DevOps Engineer",
            "description": "AWS, Kubernetes, Terraform",
            "departmentName": "Platform",
            "city": "Curitiba",
            "workplaceType": "hybrid",
            "publishedDate": "2026-02-10T08:00:00Z",
        },
    ]
}


def _make_source(name: str = "gupy_jobs") -> DataSourceConfig:
    """Helper to create a DataSourceConfig for Gupy tests."""
    return DataSourceConfig(
        name=name,
        source_type="api",
        url="https://gupy.io",
    )


# ---------------------------------------------------------------------------
# TestExtractTechStack
# ---------------------------------------------------------------------------


class TestExtractTechStack:
    """Test extract_tech_stack helper."""

    def test_extracts_from_plain_text(self) -> None:
        """Extracts known keywords from plain text."""
        result = extract_tech_stack("We use Python and React with PostgreSQL")
        assert result == ["Python", "React", "PostgreSQL"]

    def test_strips_html_tags(self) -> None:
        """HTML tags are stripped before matching."""
        result = extract_tech_stack(
            "<p>Experience with Docker and Kubernetes</p>"
        )
        assert result == ["Docker", "Kubernetes"]

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive; canonical names are returned."""
        result = extract_tech_stack("python REACT angular")
        assert result == ["Python", "React", "Angular"]

    def test_no_matches_returns_empty(self) -> None:
        """Returns [] when no tech keywords are found."""
        result = extract_tech_stack("We need a great communicator")
        assert result == []

    def test_no_duplicates(self) -> None:
        """Repeated mentions of the same keyword produce a single entry."""
        result = extract_tech_stack("Python and python and PYTHON")
        assert result == ["Python"]


# ---------------------------------------------------------------------------
# TestInferSeniority
# ---------------------------------------------------------------------------


class TestInferSeniority:
    """Test infer_seniority helper."""

    def test_english_senior(self) -> None:
        """Detects 'Senior' in English titles."""
        assert infer_seniority("Senior Software Engineer") == "senior"

    def test_portuguese_senior(self) -> None:
        """Detects 'Sênior' in Portuguese titles."""
        assert infer_seniority("Engenheiro Sênior") == "senior"

    def test_junior_abbreviation(self) -> None:
        """Detects 'Jr' abbreviation."""
        assert infer_seniority("Dev Jr") == "junior"

    def test_pleno(self) -> None:
        """Detects 'Pleno' (PT-BR mid-level)."""
        assert infer_seniority("Desenvolvedor Pleno") == "mid"

    def test_lead(self) -> None:
        """Detects 'Tech Lead' pattern."""
        assert infer_seniority("Tech Lead Backend") == "lead"

    def test_no_match(self) -> None:
        """Returns None when no seniority pattern matches."""
        assert infer_seniority("Software Engineer") is None


# ---------------------------------------------------------------------------
# TestGupyJobListing
# ---------------------------------------------------------------------------


class TestGupyJobListing:
    """Test GupyJobListing dataclass initialization."""

    def test_content_hash_from_url(self) -> None:
        """content_hash auto-computed as MD5 of the job URL."""
        url = "https://nubank.gupy.io/job/12345"
        job = GupyJobListing(
            company_slug="nubank",
            role_title="Backend Engineer",
            url=url,
        )
        assert job.content_hash == compute_content_hash(url)

    def test_authority_auto_created(self) -> None:
        """Default authority is COMMUNITY / Gupy."""
        job = GupyJobListing(
            company_slug="nubank",
            role_title="Backend Engineer",
            url="https://nubank.gupy.io/job/12345",
        )
        assert job.authority.verification_level == VerificationLevel.COMMUNITY
        assert job.authority.institution_name == "Gupy"

    def test_all_fields_populated(self) -> None:
        """All fields are stored correctly when provided."""
        custom_authority = SourceAuthority(
            verification_level=VerificationLevel.OFFICIAL,
            institution_name="Custom",
        )
        job = GupyJobListing(
            company_slug="creditas",
            role_title="Senior Frontend Dev",
            url="https://creditas.gupy.io/job/999",
            seniority="senior",
            department="Engineering",
            location="São Paulo",
            workplace_type="remote",
            tech_stack=["React", "TypeScript"],
            published_at="2026-02-01T10:00:00Z",
            authority=custom_authority,
            content_hash="custom_hash",
        )

        assert job.company_slug == "creditas"
        assert job.role_title == "Senior Frontend Dev"
        assert job.url == "https://creditas.gupy.io/job/999"
        assert job.seniority == "senior"
        assert job.department == "Engineering"
        assert job.location == "São Paulo"
        assert job.workplace_type == "remote"
        assert job.tech_stack == ["React", "TypeScript"]
        assert job.published_at == "2026-02-01T10:00:00Z"
        assert job.authority is custom_authority
        assert job.content_hash == "custom_hash"

    def test_default_values(self) -> None:
        """Optional fields default to None or empty list."""
        job = GupyJobListing(
            company_slug="nubank",
            role_title="Backend Engineer",
            url="https://nubank.gupy.io/job/12345",
        )

        assert job.seniority is None
        assert job.department is None
        assert job.location is None
        assert job.workplace_type is None
        assert job.tech_stack == []
        assert job.published_at is None
        assert job.content_hash != ""  # Auto-generated


# ---------------------------------------------------------------------------
# TestFetchGupyJobs
# ---------------------------------------------------------------------------


class TestFetchGupyJobs:
    """Test fetch_gupy_jobs function."""

    def test_successful_fetch(self) -> None:
        """Mock 1 company slug, 2 jobs returned."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GUPY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_gupy_jobs(source, client, company_slugs=["nubank"])

        assert len(result) == 2
        assert all(isinstance(j, GupyJobListing) for j in result)

        assert result[0].role_title == "Senior Software Engineer - Backend"
        assert result[0].company_slug == "nubank"
        assert result[0].department == "Engineering"
        assert result[0].location == "São Paulo"
        assert result[0].workplace_type == "remote"
        assert result[0].published_at == "2026-02-01T10:00:00Z"
        assert result[0].url == "https://nubank.gupy.io/job/12345"

        assert result[1].role_title == "Desenvolvedor Pleno Frontend"
        assert result[1].url == "https://nubank.gupy.io/job/12346"

    def test_returns_empty_for_no_slugs(self) -> None:
        """company_slugs=None returns []."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        assert fetch_gupy_jobs(source, client, company_slugs=None) == []
        assert fetch_gupy_jobs(source, client, company_slugs=[]) == []
        client.get.assert_not_called()

    def test_skips_404_slug_continues_others(self) -> None:
        """First slug 404s, second succeeds -- only second slug's jobs returned."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        # First call: 404
        mock_404_response = MagicMock()
        mock_404_response.status_code = 404
        error_404 = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_404_response,
        )

        # Second call: success
        mock_ok_response = MagicMock()
        mock_ok_response.json.return_value = SAMPLE_GUPY_RESPONSE_SECOND
        mock_ok_response.raise_for_status = MagicMock()

        def side_effect(url: str) -> MagicMock:
            if "badslug" in url:
                resp = MagicMock()
                resp.raise_for_status.side_effect = error_404
                return resp
            return mock_ok_response

        client.get.side_effect = side_effect

        result = fetch_gupy_jobs(
            source, client, company_slugs=["badslug", "goodco"]
        )

        assert len(result) == 1
        assert result[0].role_title == "DevOps Engineer"
        assert result[0].company_slug == "goodco"

    def test_returns_empty_on_http_error(self) -> None:
        """All slugs fail with HTTP errors -- returns []."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        client.get.side_effect = httpx.HTTPError("Connection failed")

        result = fetch_gupy_jobs(
            source, client, company_slugs=["failing-co"]
        )

        assert result == []

    def test_tech_stack_and_seniority_extracted(self) -> None:
        """tech_stack and seniority populated from mock data."""
        source = _make_source()
        client = MagicMock(spec=httpx.Client)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GUPY_RESPONSE
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        result = fetch_gupy_jobs(source, client, company_slugs=["nubank"])

        # First job: "Senior Software Engineer - Backend"
        # Description: Python, FastAPI, Docker, PostgreSQL
        assert result[0].seniority == "senior"
        assert "Python" in result[0].tech_stack
        assert "FastAPI" in result[0].tech_stack
        assert "Docker" in result[0].tech_stack
        assert "PostgreSQL" in result[0].tech_stack

        # Second job: "Desenvolvedor Pleno Frontend"
        # Description: React, TypeScript, Node.js
        assert result[1].seniority == "mid"
        assert "React" in result[1].tech_stack
        assert "TypeScript" in result[1].tech_stack
        assert "Node.js" in result[1].tech_stack
