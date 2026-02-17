"""Layer 5: SEO Optimization Agent (SEO.engine).

Checks and suggests SEO improvements without modifying factual content:
    1. Title length (50-60 chars ideal for search)
    2. Meta description from summary (150-160 chars)
    3. Header hierarchy (H1 -> H2 -> H3, no skips)
    4. Internal link opportunities
    5. JSON-LD Article structured data generation

Rules per editorial policy:
    - Never alter factual claims for SEO purposes
    - Never add keywords that change meaning
    - Optimization limited to: title/meta, internal linking,
      structured data, header hierarchy
    - Changes logged with [SEO] tag
"""

import json
import logging
import re
from typing import Any, Optional

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "seo"

# SEO thresholds
TITLE_MIN_LENGTH = 30
TITLE_IDEAL_MIN = 50
TITLE_IDEAL_MAX = 60
TITLE_MAX_LENGTH = 70
META_DESC_MIN = 120
META_DESC_IDEAL_MIN = 150
META_DESC_IDEAL_MAX = 160
META_DESC_MAX = 200


def run_seo(agent_output: AgentOutput) -> LayerResult:
    """Execute the SEO optimization layer.

    Checks SEO readiness without modifying factual content.
    All changes/suggestions are logged with [SEO] tag.

    Returns:
        LayerResult with SEO metadata and suggestions.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {"seo_tag": "[SEO]"}
    modifications: dict[str, Any] = {}

    title = agent_output.title or ""
    summary = agent_output.summary or ""
    body = agent_output.body_md or ""

    # --- Check 1: Title length ---
    title_flags, title_meta = _check_title(title)
    flags.extend(title_flags)
    metadata.update(title_meta)

    # --- Check 2: Meta description ---
    desc_flags, desc_meta = _check_meta_description(summary, body)
    flags.extend(desc_flags)
    metadata.update(desc_meta)
    if "suggested_meta_description" in desc_meta:
        modifications["meta_description"] = desc_meta["suggested_meta_description"]

    # --- Check 3: Header hierarchy ---
    header_flags, header_meta = _check_header_hierarchy(body)
    flags.extend(header_flags)
    metadata.update(header_meta)

    # --- Check 4: JSON-LD structured data ---
    jsonld = _generate_article_jsonld(agent_output)
    metadata["jsonld_article"] = jsonld
    modifications["jsonld"] = jsonld

    # Grade based on SEO readiness
    grade = _compute_grade(title, summary, flags)

    logger.info(
        "[%s] SEO layer: grade=%s, title_len=%d, flags=%d",
        LAYER_NAME,
        grade,
        len(title),
        len(flags),
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=True,  # SEO layer never blocks
        grade=grade,
        flags=flags,
        metadata=metadata,
        modifications=modifications,
    )


def _check_title(title: str) -> tuple:
    """Check title length for search optimization."""
    flags: list[ReviewFlag] = []
    meta: dict[str, Any] = {"title_length": len(title)}

    if len(title) < TITLE_MIN_LENGTH:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.SEO,
            message=f"[SEO] Title too short ({len(title)} chars, min {TITLE_MIN_LENGTH}) — may not rank well",
            layer=LAYER_NAME,
        ))
    elif len(title) < TITLE_IDEAL_MIN:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message=f"[SEO] Title slightly short ({len(title)} chars, ideal {TITLE_IDEAL_MIN}-{TITLE_IDEAL_MAX})",
            layer=LAYER_NAME,
        ))
    elif len(title) > TITLE_MAX_LENGTH:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.SEO,
            message=f"[SEO] Title too long ({len(title)} chars, max {TITLE_MAX_LENGTH}) — will be truncated in search results",
            layer=LAYER_NAME,
        ))
    elif len(title) > TITLE_IDEAL_MAX:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message=f"[SEO] Title slightly long ({len(title)} chars, ideal {TITLE_IDEAL_MIN}-{TITLE_IDEAL_MAX})",
            layer=LAYER_NAME,
        ))

    meta["title_in_ideal_range"] = TITLE_IDEAL_MIN <= len(title) <= TITLE_IDEAL_MAX
    return flags, meta


def _check_meta_description(summary: str, body: str) -> tuple:
    """Check and generate meta description."""
    flags: list[ReviewFlag] = []
    meta: dict[str, Any] = {}

    # Use summary as meta description, or extract from body
    description = summary.strip() if summary else ""

    if not description:
        # Extract first meaningful paragraph from body
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        for para in paragraphs:
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)  # Remove markdown links
            clean = re.sub(r"[*_`]", "", clean)  # Remove formatting
            if len(clean) > 50:
                description = clean[:META_DESC_IDEAL_MAX]
                break

    meta["meta_description_length"] = len(description)

    if not description:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.SEO,
            message="[SEO] No meta description available — summary is empty and no suitable paragraph found",
            layer=LAYER_NAME,
        ))
    elif len(description) < META_DESC_MIN:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message=f"[SEO] Meta description short ({len(description)} chars, ideal {META_DESC_IDEAL_MIN}-{META_DESC_IDEAL_MAX})",
            layer=LAYER_NAME,
        ))
    elif len(description) > META_DESC_MAX:
        description = description[:META_DESC_IDEAL_MAX].rsplit(" ", 1)[0] + "..."
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message=f"[SEO] Meta description truncated to {len(description)} chars",
            layer=LAYER_NAME,
        ))

    if description:
        meta["suggested_meta_description"] = description

    return flags, meta


def _check_header_hierarchy(body: str) -> tuple:
    """Check that headers follow proper hierarchy (H1 -> H2 -> H3)."""
    flags: list[ReviewFlag] = []
    meta: dict[str, Any] = {}

    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headers = [(len(m.group(1)), m.group(2)) for m in header_pattern.finditer(body)]

    meta["header_count"] = len(headers)
    meta["header_levels"] = [level for level, _ in headers]

    if not headers:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message="[SEO] No headers found in content — consider adding structure",
            layer=LAYER_NAME,
        ))
        return flags, meta

    # Check for skipped levels (e.g., H1 -> H3 without H2)
    prev_level = 0
    skips = 0
    for level, title in headers:
        if level > prev_level + 1 and prev_level > 0:
            skips += 1
        prev_level = level

    if skips > 0:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.SEO,
            message=f"[SEO] Header hierarchy has {skips} level skip(s) — search engines prefer sequential levels",
            layer=LAYER_NAME,
        ))

    # Check for multiple H1s
    h1_count = sum(1 for level, _ in headers if level == 1)
    if h1_count > 1:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.SEO,
            message=f"[SEO] Multiple H1 headers ({h1_count}) — typically one H1 per page is preferred",
            layer=LAYER_NAME,
        ))

    meta["h1_count"] = h1_count
    meta["hierarchy_valid"] = skips == 0

    return flags, meta


def _generate_article_jsonld(output: AgentOutput) -> dict:
    """Generate JSON-LD Article structured data."""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": output.title,
        "datePublished": output.generated_at.isoformat() if output.generated_at else None,
        "author": {
            "@type": "Organization",
            "name": "Sinal.lab",
            "url": "https://sinal.ai",
        },
        "publisher": {
            "@type": "Organization",
            "name": "Sinal.lab",
            "url": "https://sinal.ai",
        },
        "description": output.summary or "",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://sinal.ai/newsletter/{output.run_id}",
        },
    }

    if output.confidence:
        jsonld["reviewRating"] = {
            "@type": "Rating",
            "ratingValue": output.confidence.dq_display,
            "bestRating": 5,
            "worstRating": 1,
        }

    return jsonld


def _compute_grade(title: str, summary: str, flags: list) -> str:
    """Compute SEO readiness grade.

    A: Title and description in ideal range, valid hierarchy
    B: Minor issues (slightly off lengths, info flags only)
    C: Notable issues (missing description, bad hierarchy)
    """
    warning_count = sum(1 for f in flags if f.severity == FlagSeverity.WARNING)
    has_description = bool(summary and summary.strip())
    title_ok = TITLE_IDEAL_MIN <= len(title) <= TITLE_IDEAL_MAX

    if warning_count == 0 and title_ok and has_description:
        return "A"
    if warning_count <= 1:
        return "B"
    return "C"
