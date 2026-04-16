"""VOZES agent for social media collection, classification, and authority scoring.

Collects posts from Twitter/X, Reddit, Bluesky, RSS, YouTube, and web sources.
Classifies each post by theme and sub-theme, extracts entities, computes
authority scores, detects sentiment, and filters spam/self-promo/off-topic.

Outputs classified ProcessedSignals for PULSO to cluster and score.
"""

from apps.agents.vozes.agent import VozesAgent

__all__ = ["VozesAgent"]
