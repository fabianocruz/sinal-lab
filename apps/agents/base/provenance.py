"""Provenance tracking module for Sinal.lab agents.

Every data point ingested by an agent must have a provenance record
linking it back to its origin. This is the foundation of the platform's
trust framework and powers the transparency dashboards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ProvenanceRecord:
    """A record of where a piece of data came from."""

    source_url: Optional[str]
    source_name: str
    collected_at: datetime
    extraction_method: str  # api, scraper, rss, manual, community, database
    confidence: float = 0.5
    collector_agent: Optional[str] = None
    collector_run_id: Optional[str] = None
    field_name: Optional[str] = None
    raw_value: Optional[str] = None

    def __post_init__(self) -> None:
        valid_methods = {"api", "scraper", "rss", "manual", "community", "database"}
        if self.extraction_method not in valid_methods:
            raise ValueError(
                f"extraction_method must be one of {valid_methods}, "
                f"got '{self.extraction_method}'"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0-1, got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "collected_at": self.collected_at.isoformat(),
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "collector_agent": self.collector_agent,
            "collector_run_id": self.collector_run_id,
            "field_name": self.field_name,
            "raw_value": self.raw_value,
        }


class ProvenanceTracker:
    """Collects provenance records during an agent run."""

    def __init__(self) -> None:
        self.records: list[ProvenanceRecord] = []

    def track(
        self,
        source_url: Optional[str],
        source_name: str,
        extraction_method: str,
        confidence: float = 0.5,
        collector_agent: Optional[str] = None,
        collector_run_id: Optional[str] = None,
        field_name: Optional[str] = None,
        raw_value: Optional[str] = None,
    ) -> ProvenanceRecord:
        """Create and store a new provenance record.

        Returns the created record for optional further use.
        """
        record = ProvenanceRecord(
            source_url=source_url,
            source_name=source_name,
            collected_at=datetime.now(timezone.utc),
            extraction_method=extraction_method,
            confidence=confidence,
            collector_agent=collector_agent,
            collector_run_id=collector_run_id,
            field_name=field_name,
            raw_value=raw_value,
        )
        self.records.append(record)
        return record

    def get_sources(self) -> list[str]:
        """Return unique source names tracked in this run."""
        return list({r.source_name for r in self.records})

    def get_source_urls(self) -> list[str]:
        """Return unique source URLs tracked in this run."""
        return [r.source_url for r in self.records if r.source_url]

    def summary(self) -> dict:
        """Return a summary of provenance for this run."""
        methods = {}
        for r in self.records:
            methods[r.extraction_method] = methods.get(r.extraction_method, 0) + 1

        return {
            "total_records": len(self.records),
            "unique_sources": len(self.get_sources()),
            "extraction_methods": methods,
            "avg_confidence": (
                round(sum(r.confidence for r in self.records) / len(self.records), 3)
                if self.records
                else 0.0
            ),
        }
