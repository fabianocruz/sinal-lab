"""Layer 6: SINTESE_FINAL — Editorial Synthesis / Final Assembly.

Assembles validated, fact-checked, bias-reviewed, SEO-optimized
content into final publication format. Generates:
    - Byline: "Pesquisado pelo agente X, revisado pelo pipeline editorial"
    - Publication timestamp
    - Confidence badge data (DQ/AC + grade)
    - Formatted source list
    - Revision history entry
    - Final publish_ready determination
"""

import logging
from datetime import datetime, timezone
from typing import Any

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "sintese_final"

# Content type definitions for human review requirements
CONTENT_TYPES_REQUIRING_REVIEW = {"ANALYSIS", "DEEP_DIVE", "OPINION", "NEWS"}


def run_sintese_final(
    agent_output: AgentOutput,
    prior_layer_results: list = None,
) -> LayerResult:
    """Execute the SINTESE_FINAL layer.

    Generates publication metadata and determines final publish_ready
    status based on accumulated layer results.

    Args:
        agent_output: The content being reviewed.
        prior_layer_results: Results from layers 1-5 (passed by pipeline).

    Returns:
        LayerResult with publication metadata.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {}
    modifications: dict[str, Any] = {}

    if prior_layer_results is None:
        prior_layer_results = []

    # --- Generate byline ---
    agent_display = agent_output.agent_name.upper()
    byline = f"Pesquisado pelo agente {agent_display}, revisado pelo pipeline editorial Sinal.lab"
    metadata["byline"] = byline
    modifications["byline"] = byline

    # --- Publication timestamp ---
    pub_timestamp = datetime.now(timezone.utc).isoformat()
    metadata["publication_timestamp"] = pub_timestamp
    modifications["publication_timestamp"] = pub_timestamp

    # --- Confidence badge data ---
    confidence = agent_output.confidence
    badge_data = {
        "data_quality": confidence.dq_display,
        "analysis_confidence": confidence.ac_display,
        "grade": confidence.grade,
        "composite": confidence.composite,
        "source_count": confidence.source_count,
        "verified": confidence.verified,
    }
    metadata["confidence_badge"] = badge_data
    modifications["confidence_badge"] = badge_data

    # --- Formatted source list ---
    source_list = []
    for i, source in enumerate(agent_output.sources, 1):
        source_list.append({"index": i, "url": source})
    metadata["source_list"] = source_list
    modifications["source_list"] = source_list

    # --- Revision history entry ---
    revision_entry = {
        "action": "editorial_review",
        "timestamp": pub_timestamp,
        "layers_run": [lr.layer_name for lr in prior_layer_results],
        "overall_passed": all(lr.passed for lr in prior_layer_results),
    }
    metadata["revision_history"] = [revision_entry]
    modifications["revision_history"] = [revision_entry]

    # --- Content type review requirements ---
    content_type = agent_output.content_type
    metadata["content_type"] = content_type

    if content_type in CONTENT_TYPES_REQUIRING_REVIEW:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.EDITORIAL,
            message=f"Content type '{content_type}' requires mandatory human editorial review before publication",
            layer=LAYER_NAME,
        ))

    # --- Check for prior blockers ---
    prior_blockers = []
    for lr in prior_layer_results:
        for flag in lr.flags:
            if flag.severity == FlagSeverity.BLOCKER:
                prior_blockers.append(flag)

    if prior_blockers:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.EDITORIAL,
            message=f"Publication blocked: {len(prior_blockers)} blocker(s) from prior layers remain unresolved",
            layer=LAYER_NAME,
            detail="; ".join(f"[{b.layer}] {b.message}" for b in prior_blockers[:3]),
        ))

    # --- Grade and pass determination ---
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)
    all_prior_passed = all(lr.passed for lr in prior_layer_results)
    grade = _compute_grade(prior_layer_results, flags, all_prior_passed)

    metadata["all_prior_layers_passed"] = all_prior_passed
    metadata["publish_ready"] = not has_blockers and all_prior_passed

    logger.info(
        "[%s] Sintese final layer: grade=%s, publish_ready=%s, byline='%s'",
        LAYER_NAME,
        grade,
        metadata["publish_ready"],
        byline,
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=not has_blockers,
        grade=grade,
        flags=flags,
        metadata=metadata,
        modifications=modifications,
    )


def _compute_grade(
    prior_results: list,
    flags: list,
    all_prior_passed: bool,
) -> str:
    """Compute final editorial grade.

    Takes the lowest grade from all prior layers as the floor,
    then factors in any flags from this layer.
    """
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)

    if has_blockers:
        return "D"

    if not prior_results:
        return "C"

    grade_order = {"A": 4, "B": 3, "C": 2, "D": 1}
    prior_grades = [grade_order.get(lr.grade, 1) for lr in prior_results]
    min_prior = min(prior_grades)

    warning_count = sum(1 for f in flags if f.severity == FlagSeverity.WARNING)
    if warning_count > 0:
        min_prior = max(min_prior - 1, 1)

    reverse = {4: "A", 3: "B", 2: "C", 1: "D"}
    return reverse.get(min_prior, "D")
