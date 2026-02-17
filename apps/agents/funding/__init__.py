"""FUNDING — Investment Tracking Agent for Sinal.lab.

Tracks funding rounds in LATAM tech companies from VC announcements,
Dealroom API, and financial news sources. Produces weekly funding reports.
"""

from apps.agents.funding.agent import FundingAgent

__all__ = ["FundingAgent"]
