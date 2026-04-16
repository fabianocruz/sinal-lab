"""VOZES agent data models.

Re-exports shared pipeline models (SocialPost, ProcessedSignal, EntityMention)
from social_signals.models for now. When pulso/models.py is created, update
the imports to point there instead.

Adds VOZES-specific models (VoiceProfile) for tracked voice authority tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Shared pipeline models -- these will eventually live in pulso/models.py.
# For now, import from social_signals since pulso/models.py doesn't exist yet.
from apps.agents.social_signals.models import (
    EntityMention,
    ProcessedSignal,
    SocialPost,
)

__all__ = [
    "SocialPost",
    "ProcessedSignal",
    "EntityMention",
    "VoiceProfile",
]


@dataclass
class VoiceProfile:
    """Tracked voice with authority metrics.

    Represents an author/account whose signals are monitored over time.
    Authority score aggregates across all signals from this voice.
    """

    handle: str
    display_name: str
    platform: str
    authority_score: float  # 0-1
    signal_count: int = 0
    themes: list[str] = field(default_factory=list)
    first_seen: str = ""  # ISO datetime
    last_seen: str = ""  # ISO datetime
