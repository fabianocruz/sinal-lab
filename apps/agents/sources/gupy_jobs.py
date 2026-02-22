"""Shared Gupy job board source for agent collectors.

Fetches tech job listings from Gupy company career pages via their
public JSON API (``https://{slug}.gupy.io/api/job``).

Extracts tech stack mentions from job descriptions and infers seniority
levels from PT-BR and EN job titles.  Falls back gracefully (returns [])
when all company slugs fail or when the response is malformed.

Usage:
    from apps.agents.sources.gupy_jobs import (
        fetch_gupy_jobs,
        extract_tech_stack,
        infer_seniority,
    )

    jobs = fetch_gupy_jobs(source_config, client, company_slugs=["nubank", "creditas"])
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig
from apps.agents.sources.dedup import compute_content_hash
from apps.agents.sources.verification import SourceAuthority, VerificationLevel

logger = logging.getLogger(__name__)

# Curated list of tech keywords to match in job descriptions.
# Order matters: it determines output order when multiple keywords match.
TECH_KEYWORDS: List[str] = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "Go",
    "Rust",
    "Ruby",
    "PHP",
    "C#",
    ".NET",
    "React",
    "Angular",
    "Vue",
    "Node.js",
    "Django",
    "FastAPI",
    "Spring",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Kafka",
    "Terraform",
    "GraphQL",
    "REST",
]

# Pre-compiled regex patterns for each keyword (case-insensitive, word boundary).
_TECH_PATTERNS: List[tuple[str, re.Pattern[str]]] = [
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in TECH_KEYWORDS
]

# Seniority mapping: (pattern, level).
# Patterns are checked in order; first match wins.
_SENIORITY_RULES: List[tuple[str, str]] = [
    (r"\btech\s+lead\b", "lead"),
    (r"\bmid[-\s]?level\b", "mid"),
    (r"\bjunior\b", "junior"),
    (r"\bj[uú]nior\b", "junior"),
    (r"\bjr\b", "junior"),
    (r"\bpleno\b", "mid"),
    (r"\bmid\b", "mid"),
    (r"\bsenior\b", "senior"),
    (r"\bs[eê]nior\b", "senior"),
    (r"\bsr\b", "senior"),
    (r"\blead\b", "lead"),
    (r"\bl[ií]der\b", "lead"),
    (r"\bstaff\b", "staff"),
    (r"\bprincipal\b", "staff"),
    (r"\bhead\b", "director"),
    (r"\bdirector\b", "director"),
    (r"\bdiretor\b", "director"),
    (r"\bgerente\b", "director"),
]

_SENIORITY_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), level)
    for pattern, level in _SENIORITY_RULES
]

# Sentinel used to detect when authority was not explicitly provided.
_AUTHORITY_SENTINEL = object()


@dataclass
class GupyJobListing:
    """A single job listing from a Gupy company career page.

    Content hash is the MD5 of the job URL (via ``compute_content_hash``).
    Authority defaults to COMMUNITY / "Gupy" when not explicitly provided.
    """

    company_slug: str
    role_title: str
    url: str
    seniority: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    workplace_type: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    published_at: Optional[str] = None
    authority: SourceAuthority = field(default_factory=lambda: _AUTHORITY_SENTINEL)  # type: ignore[assignment]
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = compute_content_hash(self.url)
        if self.authority is _AUTHORITY_SENTINEL:
            self.authority = SourceAuthority(
                verification_level=VerificationLevel.COMMUNITY,
                institution_name="Gupy",
            )


def extract_tech_stack(description: str) -> List[str]:
    """Extract technology keywords from a job description.

    HTML tags are stripped before matching.  Matches are deduplicated
    and returned in the order they appear in ``TECH_KEYWORDS``.

    Args:
        description: Plain-text or HTML job description.

    Returns:
        Deduplicated list of matched technology keywords.
    """
    # Strip HTML tags.
    text = re.sub(r"<[^>]+>", " ", description)

    found: List[str] = []
    for canonical_name, pattern in _TECH_PATTERNS:
        if pattern.search(text) and canonical_name not in found:
            found.append(canonical_name)

    return found


def infer_seniority(title: str) -> Optional[str]:
    """Infer seniority level from a job title (PT-BR and EN).

    Args:
        title: Job title string (e.g. "Senior Software Engineer",
               "Desenvolvedor Pleno Frontend").

    Returns:
        One of "junior", "mid", "senior", "lead", "staff", "director",
        or ``None`` if no known pattern matches.
    """
    for pattern, level in _SENIORITY_PATTERNS:
        if pattern.search(title):
            return level
    return None


def fetch_gupy_jobs(
    source: DataSourceConfig,
    client: httpx.Client,
    company_slugs: Optional[List[str]] = None,
) -> List[GupyJobListing]:
    """Fetch tech job listings from Gupy company career pages.

    Iterates over ``company_slugs``, calling the public Gupy JSON API
    for each one.  Slugs that 404 are skipped; other HTTP errors are
    logged and skipped.  Results from all successful slugs are combined.

    Args:
        source: DataSourceConfig with provenance info.
        client: Pre-configured httpx.Client (caller manages lifecycle).
        company_slugs: List of Gupy company slugs (e.g. ["nubank", "creditas"]).
            If None or empty, returns [].

    Returns:
        List of GupyJobListing. Empty list when ``company_slugs`` is
        empty or when all slugs fail.
    """
    if not company_slugs:
        return []

    all_jobs: List[GupyJobListing] = []

    for slug in company_slugs:
        api_url = f"https://{slug}.gupy.io/api/job"

        try:
            response = client.get(api_url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info(
                    "Gupy slug %s returned 404, skipping", slug
                )
            else:
                logger.warning(
                    "Gupy HTTP error for slug %s: %s", slug, exc
                )
            continue
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning(
                "Gupy request error for slug %s: %s", slug, exc
            )
            continue

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(
                "Gupy JSON decode error for slug %s: %s", slug, exc
            )
            continue

        entries = data.get("data", [])

        for entry in entries:
            try:
                job_id = entry.get("id", "")
                name = entry.get("name", "")
                description = entry.get("description", "")
                department = entry.get("departmentName") or None
                city = entry.get("city") or None
                workplace_type = entry.get("workplaceType") or None
                published_date = entry.get("publishedDate") or None

                job_url = f"https://{slug}.gupy.io/job/{job_id}"
                tech_stack = extract_tech_stack(description)
                seniority = infer_seniority(name)

                all_jobs.append(
                    GupyJobListing(
                        company_slug=slug,
                        role_title=name,
                        url=job_url,
                        seniority=seniority,
                        department=department,
                        location=city,
                        workplace_type=workplace_type,
                        tech_stack=tech_stack,
                        published_at=published_date,
                    )
                )
            except Exception as exc:
                logger.debug(
                    "Skipping malformed Gupy job entry for slug %s: %s",
                    slug,
                    exc,
                )
                continue

    logger.info(
        "Fetched %d jobs from %d Gupy slug(s) for %s",
        len(all_jobs),
        len(company_slugs),
        source.name,
    )
    return all_jobs
