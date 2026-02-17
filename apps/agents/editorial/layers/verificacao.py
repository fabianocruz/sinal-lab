"""Layer 3: VERIFICACAO — Fact-Checking.

Applies structural consistency checks to drafted content:
    1. Percentage sanity (values 0-100)
    2. Temporal consistency (date/year claims)
    3. URL well-formedness
    4. Duplicate content detection (repeated paragraphs)

Uses rule-based heuristics (no LLM calls). Each check returns
green/yellow/red classification. >2 yellows or any red triggers
a blocker flag requiring human review.
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "verificacao"

# Thresholds
MAX_YELLOW_FLAGS = 2  # More than this count triggers a blocker


def run_verificacao(agent_output: AgentOutput) -> LayerResult:
    """Execute the VERIFICACAO layer on an AgentOutput.

    Runs 4 structural fact-checks and aggregates results.

    Returns:
        LayerResult with grade based on check results.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {
        "checks_run": [],
        "green_count": 0,
        "yellow_count": 0,
        "red_count": 0,
    }

    body = agent_output.body_md or ""

    # --- Check 1: Percentage sanity ---
    pct_flags = _check_percentages(body)
    flags.extend(pct_flags)
    metadata["checks_run"].append("percentage_sanity")

    # --- Check 2: Temporal consistency ---
    temporal_flags = _check_temporal_consistency(body)
    flags.extend(temporal_flags)
    metadata["checks_run"].append("temporal_consistency")

    # --- Check 3: URL well-formedness ---
    url_flags = _check_urls(body)
    flags.extend(url_flags)
    metadata["checks_run"].append("url_wellformedness")

    # --- Check 4: Duplicate content ---
    dup_flags = _check_duplicates(body)
    flags.extend(dup_flags)
    metadata["checks_run"].append("duplicate_detection")

    # Count by severity for aggregation
    red_count = sum(1 for f in flags if f.severity == FlagSeverity.ERROR)
    yellow_count = sum(1 for f in flags if f.severity == FlagSeverity.WARNING)
    green_checks = 4 - (1 if pct_flags else 0) - (1 if temporal_flags else 0) - (1 if url_flags else 0) - (1 if dup_flags else 0)

    metadata["green_count"] = green_checks
    metadata["yellow_count"] = yellow_count
    metadata["red_count"] = red_count

    # Escalation: >2 yellows or any red triggers blocker
    if red_count > 0:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.FACT_CHECK,
            message=f"Fact-check failed: {red_count} red flag(s) detected — mandatory human review",
            layer=LAYER_NAME,
        ))

    if yellow_count > MAX_YELLOW_FLAGS:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.FACT_CHECK,
            message=f"Fact-check escalation: {yellow_count} yellow flags exceed threshold ({MAX_YELLOW_FLAGS}) — mandatory human review",
            layer=LAYER_NAME,
        ))

    grade = _compute_grade(red_count, yellow_count)
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)

    logger.info(
        "[%s] Verificacao layer: grade=%s, green=%d, yellow=%d, red=%d",
        LAYER_NAME,
        grade,
        green_checks,
        yellow_count,
        red_count,
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=not has_blockers,
        grade=grade,
        flags=flags,
        metadata=metadata,
    )


def _check_percentages(body: str) -> list[ReviewFlag]:
    """Check that percentage values are within 0-100 range."""
    flags: list[ReviewFlag] = []

    # Match patterns like "150%", "234.5%", but not negative
    pct_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*%")
    matches = pct_pattern.findall(body)

    for value_str in matches:
        value = float(value_str)
        if value > 100:
            flags.append(ReviewFlag(
                severity=FlagSeverity.WARNING,
                category=FlagCategory.FACT_CHECK,
                message=f"Percentage value {value}% exceeds 100 — verify if this is a growth rate or error",
                layer=LAYER_NAME,
                detail=f"Found: {value_str}%",
            ))
        elif value < 0:
            flags.append(ReviewFlag(
                severity=FlagSeverity.ERROR,
                category=FlagCategory.FACT_CHECK,
                message=f"Negative percentage {value}% is likely an error",
                layer=LAYER_NAME,
            ))

    return flags


def _check_temporal_consistency(body: str) -> list[ReviewFlag]:
    """Check for temporal inconsistencies in the content."""
    flags: list[ReviewFlag] = []

    # Detect year references
    year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")
    years = [int(y) for y in year_pattern.findall(body)]

    if years:
        current_year = 2026  # Platform launch year
        future_years = [y for y in years if y > current_year]
        very_old_years = [y for y in years if y < 2000]

        if future_years:
            flags.append(ReviewFlag(
                severity=FlagSeverity.WARNING,
                category=FlagCategory.FACT_CHECK,
                message=f"Future year(s) referenced: {future_years} — verify these are projections, not errors",
                layer=LAYER_NAME,
            ))

        if very_old_years:
            flags.append(ReviewFlag(
                severity=FlagSeverity.INFO,
                category=FlagCategory.FACT_CHECK,
                message=f"Pre-2000 year(s) referenced: {very_old_years} — unusual for current tech content",
                layer=LAYER_NAME,
            ))

    # Detect "X years ago" inconsistencies with mentioned years
    years_ago_pattern = re.compile(r"(\d+)\s+(?:anos?\s+atr[aá]s|years?\s+ago)", re.IGNORECASE)
    for match in years_ago_pattern.finditer(body):
        n_years = int(match.group(1))
        implied_year = 2026 - n_years
        if implied_year < 1990 or n_years > 50:
            flags.append(ReviewFlag(
                severity=FlagSeverity.WARNING,
                category=FlagCategory.FACT_CHECK,
                message=f'"{match.group(0)}" implies year {implied_year} — verify this is correct',
                layer=LAYER_NAME,
            ))

    return flags


def _check_urls(body: str) -> list[ReviewFlag]:
    """Check that all URLs in the content are well-formed."""
    flags: list[ReviewFlag] = []

    # Extract URLs from markdown links and raw URLs
    md_link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    raw_url_pattern = re.compile(r"(?<!\()(https?://[^\s\)\"'>]+)")

    urls: list[str] = []
    for _, url in md_link_pattern.findall(body):
        urls.append(url)
    for url in raw_url_pattern.findall(body):
        urls.append(url)

    malformed_count = 0
    for url in urls:
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                malformed_count += 1
        except Exception:
            malformed_count += 1

    if malformed_count > 0:
        severity = FlagSeverity.ERROR if malformed_count > 3 else FlagSeverity.WARNING
        flags.append(ReviewFlag(
            severity=severity,
            category=FlagCategory.FACT_CHECK,
            message=f"{malformed_count} malformed URL(s) detected out of {len(urls)} total",
            layer=LAYER_NAME,
        ))

    return flags


def _check_duplicates(body: str) -> list[ReviewFlag]:
    """Detect duplicate paragraphs or sentences in the content."""
    flags: list[ReviewFlag] = []

    # Split into paragraphs (non-empty lines separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]

    # Check for duplicate paragraphs (ignoring very short ones like "---")
    meaningful_paragraphs = [p for p in paragraphs if len(p) > 30]
    seen_paragraphs: dict[str, int] = {}
    duplicates = 0

    for para in meaningful_paragraphs:
        normalized = para.lower().strip()
        if normalized in seen_paragraphs:
            duplicates += 1
        else:
            seen_paragraphs[normalized] = 1

    if duplicates > 0:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.FACT_CHECK,
            message=f"{duplicates} duplicate paragraph(s) detected",
            layer=LAYER_NAME,
            detail="Repeated content may indicate a synthesis error",
        ))

    return flags


def _compute_grade(red_count: int, yellow_count: int) -> str:
    """Compute fact-check grade.

    A: All green (no issues)
    B: 1-2 yellow flags (minor concerns)
    C: >2 yellow flags (needs attention)
    D: Any red flags (serious issues)
    """
    if red_count > 0:
        return "D"
    if yellow_count > MAX_YELLOW_FLAGS:
        return "C"
    if yellow_count > 0:
        return "B"
    return "A"
