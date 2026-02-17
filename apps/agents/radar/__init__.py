"""RADAR — Trend Intelligence Agent for Sinal.lab.

Detects emerging trends in the LATAM tech ecosystem from HN, GitHub,
Google Trends, and arXiv. Produces a weekly trend synthesis report.
"""

from apps.agents.radar.agent import RadarAgent

__all__ = ["RadarAgent"]
