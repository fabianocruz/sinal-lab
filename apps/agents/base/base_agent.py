"""BaseAgent — abstract base class for all Sinal.lab AI agents.

Every agent follows the lifecycle: collect -> process -> score -> output.
Subclasses must implement each step. The run() method orchestrates them.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from apps.agents.base.confidence import ConfidenceScore
from apps.agents.base.output import AgentOutput
from apps.agents.base.provenance import ProvenanceTracker

import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all platform AI agents.

    Subclasses implement:
        - collect(): gather raw data from configured sources
        - process(): transform, classify, and filter collected data
        - score(): compute confidence scores for processed data
        - output(): format results into publishable content
    """

    agent_name: str = "base"
    version: str = "0.1.0"

    def __init__(self) -> None:
        self.run_id: str = f"{self.agent_name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.provenance: ProvenanceTracker = ProvenanceTracker()
        self._collected_data: list[Any] = []
        self._processed_data: list[Any] = []
        self._scores: list[ConfidenceScore] = []
        self._errors: list[str] = []

    @abstractmethod
    def collect(self) -> list[Any]:
        """Gather raw data from configured sources.

        Returns a list of raw data items. Each item should be a dict
        with at least a 'source' key for provenance tracking.
        """
        ...

    @abstractmethod
    def process(self, raw_data: list[Any]) -> list[Any]:
        """Transform, classify, and filter collected data.

        Takes raw data from collect() and returns processed items
        ready for confidence scoring.
        """
        ...

    @abstractmethod
    def score(self, processed_data: list[Any]) -> list[ConfidenceScore]:
        """Compute confidence scores for processed data.

        Returns a list of ConfidenceScore objects, one per item
        or one aggregate score for the entire output.
        """
        ...

    @abstractmethod
    def output(self, processed_data: list[Any], scores: list[ConfidenceScore]) -> AgentOutput:
        """Format results into publishable content.

        Returns an AgentOutput containing Markdown content with
        YAML frontmatter, ready for the editorial pipeline.
        """
        ...

    def run(self) -> AgentOutput:
        """Execute the full agent lifecycle: collect -> process -> score -> output.

        Returns the final AgentOutput. Catches and logs errors at each step.
        """
        self.started_at = datetime.now(timezone.utc)
        logger.info(
            "Agent %s starting run %s",
            self.agent_name,
            self.run_id,
        )

        try:
            # Step 1: Collect
            logger.info("[%s] Step 1/4: Collecting data...", self.run_id)
            self._collected_data = self.collect()
            logger.info(
                "[%s] Collected %d items", self.run_id, len(self._collected_data)
            )

            # Step 2: Process
            logger.info("[%s] Step 2/4: Processing data...", self.run_id)
            self._processed_data = self.process(self._collected_data)
            logger.info(
                "[%s] Processed %d items", self.run_id, len(self._processed_data)
            )

            # Step 3: Score
            logger.info("[%s] Step 3/4: Computing confidence scores...", self.run_id)
            self._scores = self.score(self._processed_data)
            logger.info("[%s] Scored %d items", self.run_id, len(self._scores))

            # Step 4: Output
            logger.info("[%s] Step 4/4: Generating output...", self.run_id)
            result = self.output(self._processed_data, self._scores)

            self.completed_at = datetime.now(timezone.utc)
            logger.info(
                "[%s] Run completed in %.2fs",
                self.run_id,
                (self.completed_at - self.started_at).total_seconds(),
            )

            return result

        except Exception as e:
            self.completed_at = datetime.now(timezone.utc)
            self._errors.append(str(e))
            logger.error("[%s] Run failed: %s", self.run_id, e, exc_info=True)
            raise

    def get_run_metadata(self) -> dict[str, Any]:
        """Return metadata about this run for logging and transparency."""
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "items_collected": len(self._collected_data),
            "items_processed": len(self._processed_data),
            "scores_count": len(self._scores),
            "error_count": len(self._errors),
            "provenance_records": len(self.provenance.records),
        }
