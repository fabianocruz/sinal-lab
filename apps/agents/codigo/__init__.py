"""CODIGO — Developer Ecosystem Signals Agent for Sinal.lab.

Tracks GitHub trending repos, npm/PyPI package momentum, and
Stack Overflow trends to produce a weekly dev ecosystem report.
"""

from apps.agents.codigo.agent import CodigoAgent

__all__ = ["CodigoAgent"]
