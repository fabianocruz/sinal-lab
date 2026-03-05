"""Output formatting module for Sinal.lab agents.

Agent outputs are Markdown documents with YAML frontmatter containing
metadata (agent name, run ID, confidence scores, sources). This module
handles formatting, serialization, and validation of agent outputs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from apps.agents.base.confidence import ConfidenceScore


@dataclass
class AgentOutput:
    """The formatted output of an agent run."""

    title: str
    body_md: str
    agent_name: str
    run_id: str
    confidence: ConfidenceScore
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[str] = field(default_factory=list)
    content_type: str = "DATA_REPORT"
    agent_category: str = "content"
    summary: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    llm_used: bool = False

    def to_markdown(self) -> str:
        """Render the full output as Markdown with YAML frontmatter."""
        frontmatter_lines = [
            "---",
            f"title: \"{self.title}\"",
            f"agent: {self.agent_name}",
            f"run_id: \"{self.run_id}\"",
            f"generated_at: \"{self.generated_at.isoformat()}\"",
            f"content_type: {self.content_type}",
            f"agent_category: {self.agent_category}",
            f"confidence_dq: {self.confidence.data_quality}",
            f"confidence_ac: {self.confidence.analysis_confidence}",
            f"confidence_grade: {self.confidence.grade}",
            f"source_count: {self.confidence.source_count}",
            f"llm_used: {str(self.llm_used).lower()}",
        ]

        if self.sources:
            frontmatter_lines.append("sources:")
            for source in self.sources:
                frontmatter_lines.append(f"  - \"{source}\"")

        if self.summary:
            frontmatter_lines.append(f"summary: \"{self.summary}\"")

        frontmatter_lines.append("---")
        frontmatter = "\n".join(frontmatter_lines)

        return f"{frontmatter}\n\n{self.body_md}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage in the database or API responses."""
        return {
            "title": self.title,
            "body_md": self.body_md,
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "generated_at": self.generated_at.isoformat(),
            "content_type": self.content_type,
            "agent_category": self.agent_category,
            "confidence": self.confidence.to_dict(),
            "sources": self.sources,
            "summary": self.summary,
            "metadata": self.metadata,
            "llm_used": self.llm_used,
        }

    def validate(self) -> list[str]:
        """Check output meets minimum quality standards.

        Returns a list of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not self.title or not self.title.strip():
            errors.append("Title is required")

        if not self.body_md or not self.body_md.strip():
            errors.append("Body markdown is required")

        word_count = len(self.body_md.split())
        if word_count < 50:
            errors.append(f"Body too short ({word_count} words, minimum 50)")

        if self.confidence.composite < 0.1:
            errors.append(
                f"Confidence too low ({self.confidence.composite}), "
                "review data sources"
            )

        if not self.sources:
            errors.append("At least one source is required")

        return errors


def format_markdown_output(
    title: str,
    sections: list[dict[str, str]],
    agent_name: str,
    run_id: str,
    confidence: ConfidenceScore,
    sources: list[str],
    content_type: str = "DATA_REPORT",
    agent_category: str = "content",
    summary: Optional[str] = None,
) -> AgentOutput:
    """Helper to build an AgentOutput from structured sections.

    Args:
        title: The output title.
        sections: List of {"heading": "...", "content": "..."} dicts.
        agent_name: Name of the producing agent.
        run_id: Unique run identifier.
        confidence: Confidence score for this output.
        sources: List of source URLs or names.
        content_type: Classification (DATA_REPORT, ANALYSIS, etc.).
        agent_category: Agent scope (data, content, quality).
        summary: Optional one-paragraph summary.

    Returns:
        A fully formed AgentOutput.
    """
    body_parts: list[str] = [f"# {title}", ""]

    if summary:
        body_parts.extend([f"*{summary}*", ""])

    for section in sections:
        heading = section.get("heading", "")
        content = section.get("content", "")
        if heading:
            body_parts.append(f"## {heading}")
            body_parts.append("")
        if content:
            body_parts.append(content)
            body_parts.append("")

    body_md = "\n".join(body_parts)

    return AgentOutput(
        title=title,
        body_md=body_md,
        agent_name=agent_name,
        run_id=run_id,
        confidence=confidence,
        sources=sources,
        content_type=content_type,
        agent_category=agent_category,
        summary=summary,
    )
