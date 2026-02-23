"""INDEX pipeline — convert, deduplicate, and merge company records.

Orchestrates the full pipeline from multi-source raw data through
entity matching to merged, scored company records ready for persistence.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from apps.agents.sources.entity_matcher import (
    CandidateCompany,
    DedupIndices,
    MatchResult,
    match_batch,
)

logger = logging.getLogger(__name__)


@dataclass
class MergedCompany:
    """A company record after cross-source merge.

    Combines data from multiple sources with the best-confidence
    value for each field.
    """

    slug: str
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Brasil"
    cnpj: Optional[str] = None
    domain: Optional[str] = None
    crunchbase_permalink: Optional[str] = None
    github_login: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    founded_date: Optional[str] = None
    team_size: Optional[int] = None
    business_model: Optional[str] = None
    tech_stack: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_count: int = 1
    sources: list[str] = field(default_factory=list)
    best_confidence: float = 0.0
    is_new: bool = True


def _merge_field(existing, new):
    """Return the first non-None/non-empty value."""
    if new and not existing:
        return new
    return existing


def _merge_into(merged: MergedCompany, candidate: CandidateCompany) -> None:
    """Merge a candidate's data into an existing MergedCompany.

    Non-null fields from the candidate fill in gaps; lists are merged.
    Source count is incremented.
    """
    merged.website = _merge_field(merged.website, candidate.website)
    merged.description = _merge_field(merged.description, candidate.description)
    merged.sector = _merge_field(merged.sector, candidate.sector)
    merged.city = _merge_field(merged.city, candidate.city)
    merged.state = _merge_field(merged.state, candidate.state)
    merged.cnpj = _merge_field(merged.cnpj, candidate.cnpj)
    merged.domain = _merge_field(merged.domain, candidate.domain)
    merged.crunchbase_permalink = _merge_field(merged.crunchbase_permalink, candidate.crunchbase_permalink)
    merged.github_login = _merge_field(merged.github_login, candidate.github_login)
    merged.github_url = _merge_field(merged.github_url, candidate.github_url)
    merged.linkedin_url = _merge_field(merged.linkedin_url, candidate.linkedin_url)
    merged.twitter_url = _merge_field(merged.twitter_url, candidate.twitter_url)
    merged.founded_date = _merge_field(merged.founded_date, candidate.founded_date)
    merged.team_size = _merge_field(merged.team_size, candidate.team_size)
    merged.business_model = _merge_field(merged.business_model, candidate.business_model)

    # Merge lists (deduplicated)
    if candidate.tech_stack:
        existing = set(merged.tech_stack)
        merged.tech_stack = sorted(existing | set(candidate.tech_stack))

    if candidate.tags:
        existing = set(merged.tags)
        merged.tags = sorted(existing | set(candidate.tags))

    # Track sources
    if candidate.source_name and candidate.source_name not in merged.sources:
        merged.sources.append(candidate.source_name)
        merged.source_count = len(merged.sources)

    # Update confidence if this source is higher
    if candidate.confidence > merged.best_confidence:
        merged.best_confidence = candidate.confidence


def _create_merged(candidate: CandidateCompany) -> MergedCompany:
    """Create a new MergedCompany from a candidate."""
    slug = candidate.slug or candidate.name.lower().replace(" ", "-")

    return MergedCompany(
        slug=slug,
        name=candidate.name,
        website=candidate.website,
        description=candidate.description,
        sector=candidate.sector,
        city=candidate.city,
        state=candidate.state,
        country=candidate.country,
        cnpj=candidate.cnpj,
        domain=candidate.domain,
        crunchbase_permalink=candidate.crunchbase_permalink,
        github_login=candidate.github_login,
        github_url=candidate.github_url,
        linkedin_url=candidate.linkedin_url,
        twitter_url=candidate.twitter_url,
        founded_date=candidate.founded_date,
        team_size=candidate.team_size,
        business_model=candidate.business_model,
        tech_stack=list(candidate.tech_stack),
        tags=list(candidate.tags),
        source_count=1,
        sources=[candidate.source_name] if candidate.source_name else [],
        best_confidence=candidate.confidence,
        is_new=True,
    )


def run_pipeline(
    candidates: list[CandidateCompany],
    indices: DedupIndices,
) -> list[MergedCompany]:
    """Run the full INDEX pipeline: match and merge candidates.

    Steps:
    1. Match batch against existing DB indices + intra-batch dedup
    2. Group candidates by matched slug (or new slug for new companies)
    3. Merge all candidates for the same company
    4. Return list of MergedCompany

    Args:
        candidates: List of CandidateCompany from all sources.
        indices: Pre-built dedup indices from DB.

    Returns:
        List of MergedCompany objects (new + updated).
    """
    if not candidates:
        return []

    # Step 1: Match
    match_results = match_batch(candidates, indices)

    # Step 2: Group by slug
    slug_groups: dict[str, list[CandidateCompany]] = {}
    slug_is_new: dict[str, bool] = {}

    for candidate, result in match_results:
        if result.is_new:
            slug = candidate.slug or candidate.name.lower().replace(" ", "-")
            slug_is_new[slug] = True
        else:
            slug = result.matched_slug
            slug_is_new.setdefault(slug, False)

        slug_groups.setdefault(slug, []).append(candidate)

    # Step 3: Merge
    merged_companies: list[MergedCompany] = []

    for slug, group in slug_groups.items():
        merged = _create_merged(group[0])
        merged.slug = slug
        merged.is_new = slug_is_new.get(slug, True)

        for candidate in group[1:]:
            _merge_into(merged, candidate)

        merged_companies.append(merged)

    new_count = sum(1 for m in merged_companies if m.is_new)
    update_count = len(merged_companies) - new_count

    logger.info(
        "Pipeline complete: %d candidates → %d merged companies (%d new, %d updates)",
        len(candidates),
        len(merged_companies),
        new_count,
        update_count,
    )

    return merged_companies
