"""AgentRun model — execution logs for AI agent runs."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.database.models.base import Base, TimestampMixin, UUIDMixin


class AgentRun(UUIDMixin, TimestampMixin, Base):
    """A record of a single AI agent execution.

    Every time an agent runs (RADAR, SINTESE, CODIGO, etc.), it creates
    an AgentRun record with its inputs, outputs, timing, and quality metrics.
    These records power the agent transparency dashboards.
    """

    __tablename__ = "agent_runs"

    # Identity
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running", index=True
    )  # running, completed, failed, cancelled

    # Metrics
    items_collected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    items_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    items_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Quality
    avg_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_distribution: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Data sources accessed
    data_sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Output reference
    output_content_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AgentRun(agent='{self.agent_name}', "
            f"run_id='{self.run_id}', status='{self.status}')>"
        )
