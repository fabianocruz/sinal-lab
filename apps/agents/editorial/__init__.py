"""Editorial governance pipeline for Sinal.lab.

6-layer sequential review pipeline that takes AgentOutput from any
agent and verifies it for publication readiness:

    PESQUISA -> VALIDACAO -> VERIFICACAO -> VIES -> SEO -> SINTESE_FINAL
"""

from apps.agents.editorial.pipeline import EditorialPipeline

__all__ = ["EditorialPipeline"]
