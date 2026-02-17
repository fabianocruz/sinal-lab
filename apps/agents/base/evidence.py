"""Unified evidence model for cross-agent operations.

EvidenceItem is the shared data contract that all agent-specific types
(FeedItem, TrendSignal, DevSignal, FundingEvent, CompanyProfile) can
be converted to. It's not a replacement — agents keep their domain types —
but a common representation for downstream consumers: deduplication,
editorial review, entity resolution, and publishing.

Usage:
    from apps.agents.base.evidence import EvidenceItem, EvidenceType

    item = EvidenceItem(
        title="Show HN: New AI Framework",
        url="https://news.ycombinator.com/item?id=12345",
        source_name="hn_best",
        evidence_type=EvidenceType.ARTICLE,
        agent_name="sintese",
    )
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from apps.agents.base.provenance import ProvenanceRecord


class EvidenceType(str, Enum):
    """Types of evidence collected across all agents."""

    ARTICLE = "article"
    REPO = "repo"
    PACKAGE = "package"
    FUNDING_EVENT = "funding_event"
    COMPANY_PROFILE = "company_profile"
    TWEET = "tweet"


@dataclass
class EvidenceItem:
    """Unified evidence model for cross-agent operations.

    Required fields: title, url, source_name, evidence_type, agent_name.
    All other fields are optional with sensible defaults.
    """

    title: str
    url: str
    source_name: str
    evidence_type: EvidenceType
    agent_name: str
    content_hash: str = ""
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    territory: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[ProvenanceRecord] = None

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.url.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage/transport."""
        return {
            "title": self.title,
            "url": self.url,
            "source_name": self.source_name,
            "evidence_type": self.evidence_type.value,
            "agent_name": self.agent_name,
            "content_hash": self.content_hash,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "summary": self.summary,
            "author": self.author,
            "tags": self.tags,
            "confidence": self.confidence,
            "territory": self.territory,
            "metrics": self.metrics,
            "raw_data": self.raw_data,
        }
