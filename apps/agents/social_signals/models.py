"""Internal dataclasses for the Social Signals agent pipeline.

These are in-memory processing models, NOT database models. DB models
live in packages/database/models/. These dataclasses flow through the
agent pipeline: collect -> classify -> cluster -> score -> output.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SocialPost:
    """Unified post across all social platforms.

    Normalizes Twitter, LinkedIn, Reddit, and Bluesky posts into a
    single structure for processing. Platform-specific fields (like
    retweet_count) are stored in the metrics dict.
    """

    text: str
    url: str
    platform: str  # twitter, linkedin, reddit, bluesky, rss
    author_handle: str = ""
    author_display_name: str = ""
    author_followers: int = 0
    published_at: Optional[datetime] = None
    external_url: Optional[str] = None
    image_url: Optional[str] = None
    source_name: str = ""
    metrics: Dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_input = self.external_url or self.url
            self.content_hash = hashlib.md5(hash_input.encode()).hexdigest()


@dataclass
class SignalDimensions:
    """8-dimension scoring for a signal cluster.

    Each dimension is a float 0-1. The composite score is a weighted
    average defined by DIMENSION_WEIGHTS in config.py.
    """

    volume: float = 0.0
    velocity: float = 0.0
    authority_concentration: float = 0.0
    cross_platform_propagation: float = 0.0
    sentiment_shift: float = 0.0
    new_entrants: float = 0.0
    narrative_maturity: float = 0.0
    commercial_signals: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "volume": round(self.volume, 3),
            "velocity": round(self.velocity, 3),
            "authority_concentration": round(self.authority_concentration, 3),
            "cross_platform_propagation": round(self.cross_platform_propagation, 3),
            "sentiment_shift": round(self.sentiment_shift, 3),
            "new_entrants": round(self.new_entrants, 3),
            "narrative_maturity": round(self.narrative_maturity, 3),
            "commercial_signals": round(self.commercial_signals, 3),
        }

    def composite_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Compute weighted composite score.

        Args:
            weights: Optional custom weights. Defaults to equal weighting.

        Returns:
            Float 0-1 composite score.
        """
        if weights is None:
            from apps.agents.social_signals.config import DIMENSION_WEIGHTS
            weights = DIMENSION_WEIGHTS

        total = 0.0
        for dim, weight in weights.items():
            total += getattr(self, dim, 0.0) * weight
        return round(min(1.0, total), 3)


@dataclass
class EntityMention:
    """Named entity extracted from a social post."""

    name: str
    entity_type: str  # company, person, product, technology, regulation
    confidence: float = 0.5


@dataclass
class ProcessedSignal:
    """A social post enriched with classification and scoring."""

    post: SocialPost
    theme: str = ""
    sub_theme: str = ""
    entities: List[EntityMention] = field(default_factory=list)
    sentiment: float = 0.0  # -1 to 1
    authority_score: float = 0.0  # 0 to 1
    is_commercial: bool = False  # mentions product launch, funding, hiring

    @property
    def content_hash(self) -> str:
        return self.post.content_hash


@dataclass
class SignalClusterResult:
    """A group of related ProcessedSignals forming a trend or signal.

    Clusters are the primary unit of analysis in the Weekly Pulse.
    """

    name: str
    slug: str = ""
    theme: str = ""
    sub_theme: str = ""
    description: str = ""
    signals: List[ProcessedSignal] = field(default_factory=list)
    dimensions: Optional[SignalDimensions] = None
    narrative_stage: str = "emerging"  # emerging, accelerating, peaking, declining
    top_voices: List[Dict] = field(default_factory=list)
    top_posts: List[Dict] = field(default_factory=list)
    related_companies: List[Dict] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def composite_score(self) -> float:
        if self.dimensions:
            return self.dimensions.composite_score()
        return 0.0

    @property
    def platforms(self) -> List[str]:
        return list(set(s.post.platform for s in self.signals))
