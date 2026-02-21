"""Guidelines layer — validates content against packages/editorial/.

This layer runs the GuidelinesPack (territory classification + content
validation) and converts the result to a LayerResult with appropriate
flags. Not included in the default pipeline chain — opt in via
pipeline.register_layer("guidelines", run_guidelines).
"""

import logging

from apps.agents.base.output import AgentOutput
from apps.agents.editorial.guidelines_pack import GuidelinesPack
from apps.agents.editorial.models import (
    FlagCategory,
    FlagSeverity,
    LayerResult,
    ReviewFlag,
)

logger = logging.getLogger(__name__)


def run_guidelines(agent_output: AgentOutput) -> LayerResult:
    """Layer: validate against editorial guidelines (packages/editorial/).

    Runs territory classification and 5-criteria content validation.
    Produces:
    - BLOCKER flags for red flags (press releases, hype without data)
    - WARNING flags for failed validation (criteria not met)
    - No flags for clean, passing content

    Args:
        agent_output: The AgentOutput to validate.

    Returns:
        LayerResult with pass/fail and flags.
    """
    pack = GuidelinesPack()
    result = pack.evaluate_agent_output(agent_output)

    flags = []

    # Red flags → BLOCKER
    for red_flag in result.validation.red_flags:
        flags.append(ReviewFlag(
            severity=FlagSeverity.BLOCKER,
            category=FlagCategory.EDITORIAL,
            message="Red flag: {}".format(red_flag),
            layer="guidelines",
        ))

    # Failed validation (no red flags) → WARNING
    if not result.passes_guidelines and not result.validation.red_flags:
        failed_criteria = [
            k for k, v in result.validation.criteria_met.items() if not v
        ]
        flags.append(ReviewFlag(
            severity=FlagSeverity.WARNING,
            category=FlagCategory.EDITORIAL,
            message="Guidelines validation failed: criteria not met: {}".format(
                ", ".join(failed_criteria)
            ),
            layer="guidelines",
        ))

    # Recommendations → INFO
    for rec in result.validation.recommendations:
        flags.append(ReviewFlag(
            severity=FlagSeverity.INFO,
            category=FlagCategory.EDITORIAL,
            message=rec,
            layer="guidelines",
        ))

    passed = result.passes_guidelines
    grade = "A" if passed else ("D" if result.validation.red_flags else "C")

    return LayerResult(
        layer_name="guidelines",
        passed=passed,
        grade=grade,
        flags=flags,
        metadata={
            "territory": result.territory.primary_territory,
            "territory_confidence": result.territory.confidence,
            "territory_weight": result.territory_weight,
            "score": result.validation.score,
            "weighted_score": result.validation.weighted_score,
        },
    )
