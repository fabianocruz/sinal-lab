"""GuidelinesPack — facade wrapping packages/editorial/ for the editorial pipeline.

Connects the territory classifier and content validator from packages/editorial/
into a clean interface used by the editorial pipeline layers.

Usage:
    from apps.agents.editorial.guidelines_pack import GuidelinesPack

    pack = GuidelinesPack()
    result = pack.evaluate(content="...", title="...")
    if result.passes_guidelines:
        print("Content ready for publication")
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from apps.agents.base.output import AgentOutput
from packages.editorial.classifier import TerritoryClassification, classify_territory
from packages.editorial.guidelines import get_territory_weight
from packages.editorial.validator import ContentValidationResult, validate_content


@dataclass
class GuidelinesResult:
    """Result of running content through editorial guidelines."""

    territory: TerritoryClassification
    validation: ContentValidationResult
    passes_guidelines: bool
    territory_weight: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "territory": self.territory.to_dict(),
            "validation": self.validation.to_dict(),
            "passes_guidelines": self.passes_guidelines,
            "territory_weight": self.territory_weight,
            "summary": self.summary,
        }


class GuidelinesPack:
    """Facade wrapping packages/editorial/ for use in the editorial pipeline."""

    def __init__(self, strict_mode: bool = False) -> None:
        self.strict_mode = strict_mode

    def evaluate(
        self,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> GuidelinesResult:
        """Run territory classification + content validation.

        Args:
            content: The full text content to evaluate.
            title: Optional title (gets higher weight in classification).
            metadata: Optional metadata dict (sources, tags, etc.).

        Returns:
            GuidelinesResult with territory, validation, and pass/fail.
        """
        territory = classify_territory(content, title, metadata)
        validation = validate_content(
            content=content,
            metadata=metadata,
            title=title,
            strict_mode=self.strict_mode,
        )

        territory_weight = get_territory_weight(territory.primary_territory)

        status = "PASSA" if validation.passes_editorial_bar else "NÃO PASSA"
        summary = "{} | {} | Score: {}/5.0 | Território: {}".format(
            status,
            validation.summary(),
            validation.score,
            territory.primary_territory,
        )

        return GuidelinesResult(
            territory=territory,
            validation=validation,
            passes_guidelines=validation.passes_editorial_bar,
            territory_weight=territory_weight,
            summary=summary,
        )

    def evaluate_agent_output(self, agent_output: AgentOutput) -> GuidelinesResult:
        """Convenience: extract content from AgentOutput and evaluate.

        Args:
            agent_output: The agent output to evaluate.

        Returns:
            GuidelinesResult.
        """
        metadata = dict(agent_output.metadata) if agent_output.metadata else {}
        if agent_output.sources:
            metadata["sources"] = agent_output.sources

        return self.evaluate(
            content=agent_output.body_md,
            title=agent_output.title,
            metadata=metadata,
        )
