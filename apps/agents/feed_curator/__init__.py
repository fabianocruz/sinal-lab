"""Feed Curator Agent — AI-powered editorial curation of social signals.

Loads recent signals from the database, filters spam and noise via LLM,
and produces a curated feed of the top items with editorial headlines
and context in pt-BR. Persona: Ana Torres.

This is a CONTENT agent: it applies editorial judgment to raw signal data
collected by the Social Signals agent.
"""

from apps.agents.feed_curator.agent import FeedCuratorAgent

__all__ = ["FeedCuratorAgent"]
