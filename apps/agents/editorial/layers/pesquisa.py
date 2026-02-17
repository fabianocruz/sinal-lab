"""Layer 1: PESQUISA — Research / Provenance Validation.

Validates that the agent output has complete provenance data:
source URLs present, confidence scores populated, source_count > 0,
body meets minimum length. Does not analyze or interpret — only
checks structural completeness of the research inputs.
"""

import logging
from typing import Any

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)

LAYER_NAME = "pesquisa"
MIN_WORD_COUNT = 50
MIN_SOURCE_COUNT = 1
MIN_CONFIDENCE_COMPOSITE = 0.1


def run_pesquisa(agent_output: AgentOutput) -> LayerResult:
    """Execute the PESQUISA layer on an AgentOutput.

    Checks:
        1. Title is non-empty
        2. Body has minimum word count
        3. At least 1 source is listed
        4. Confidence scores are populated and above floor
        5. Source URLs are valid strings (non-empty)
        6. Agent name and run_id are present

    Returns:
        LayerResult with grade A-D based on provenance completeness.
    """
    flags: list[ReviewFlag] = []
    metadata: dict[str, Any] = {}

    # --- Structural validation (reuses AgentOutput.validate logic) ---
    validation_errors = agent_output.validate()
    for error_msg in validation_errors:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.PROVENANCE,
            message=error_msg,
            layer=LAYER_NAME,
        ))

    # --- Provenance depth checks ---
    source_count = agent_output.confidence.source_count
    metadata["source_count"] = source_count
    metadata["source_urls"] = len(agent_output.sources)
    metadata["word_count"] = len(agent_output.body_md.split()) if agent_output.body_md else 0

    if not agent_output.agent_name or not agent_output.agent_name.strip():
        flags.append(ReviewFlag(
            severity=FlagSeverity.ERROR,
            category=FlagCategory.PROVENANCE,
            message="Agent name is missing",
            layer=LAYER_NAME,
        ))

    if not agent_output.run_id or not agent_output.run_id.strip():
        flags.append(ReviewFlag(
            severity=FlagSeverity.ERROR,
            category=FlagCategory.PROVENANCE,
            message="Run ID is missing",
            layer=LAYER_NAME,
        ))

    # Source URL quality
    empty_sources = [s for s in agent_output.sources if not s or not s.strip()]
    if empty_sources:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.PROVENANCE,
            message=f"{len(empty_sources)} empty source URL(s) found",
            layer=LAYER_NAME,
        ))

    # Confidence floor
    if agent_output.confidence.composite < MIN_CONFIDENCE_COMPOSITE:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.PROVENANCE,
            message=f"Confidence too low ({agent_output.confidence.composite}), minimum {MIN_CONFIDENCE_COMPOSITE}",
            layer=LAYER_NAME,
        ))

    # Source count assessment
    if source_count == 0:
        flags.append(ReviewFlag(
            severity=FlagSeverity.ERROR,
            category=FlagCategory.PROVENANCE,
            message="No sources tracked in confidence score (source_count=0)",
            layer=LAYER_NAME,
        ))
    elif source_count == 1:
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.PROVENANCE,
            message="Only 1 source tracked — consider multi-source validation",
            layer=LAYER_NAME,
        ))

    # --- Grade assignment ---
    grade = _compute_grade(agent_output, flags)
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)

    logger.info(
        "[%s] Pesquisa layer: grade=%s, flags=%d, blockers=%s",
        LAYER_NAME,
        grade,
        len(flags),
        has_blockers,
    )

    return LayerResult(
        layer_name=LAYER_NAME,
        passed=not has_blockers,
        grade=grade,
        flags=flags,
        metadata=metadata,
    )


def _compute_grade(output: AgentOutput, flags: list[ReviewFlag]) -> str:
    """Compute grade based on provenance completeness."""
    has_blockers = any(f.severity == FlagSeverity.BLOCKER for f in flags)
    error_count = sum(1 for f in flags if f.severity == FlagSeverity.ERROR)
    warning_count = sum(1 for f in flags if f.severity == FlagSeverity.WARNING)

    if has_blockers:
        return "D"

    source_count = output.confidence.source_count
    has_sources = len(output.sources) > 0
    has_summary = output.summary is not None and len(output.summary.strip()) > 0

    if error_count > 0:
        return "C"

    if source_count >= 3 and has_sources and has_summary and warning_count == 0:
        return "A"

    if source_count >= 2 and has_sources:
        return "B" if warning_count == 0 else "C"

    return "C"
