"""Centralized persona lookup for all Sinal.lab agents.

Lazily imports each agent's config to avoid circular imports and builds
a registry mapping agent names to their AgentPersona instances.
"""

from typing import Optional

from apps.agents.base.config import AgentPersona

# Lazy-initialized cache
_registry: Optional[dict[str, AgentPersona]] = None


def _build_registry() -> dict[str, AgentPersona]:
    """Import each agent config and collect personas.

    Each import is wrapped in a try/except so a broken agent config
    does not prevent other personas from loading.
    """
    registry: dict[str, AgentPersona] = {}

    try:
        from apps.agents.sintese.config import SINTESE_CONFIG
        if SINTESE_CONFIG.persona is not None:
            registry[SINTESE_CONFIG.agent_name] = SINTESE_CONFIG.persona
    except ImportError:
        pass

    try:
        from apps.agents.radar.config import RADAR_CONFIG
        if RADAR_CONFIG.persona is not None:
            registry[RADAR_CONFIG.agent_name] = RADAR_CONFIG.persona
    except ImportError:
        pass

    try:
        from apps.agents.codigo.config import CODIGO_CONFIG
        if CODIGO_CONFIG.persona is not None:
            registry[CODIGO_CONFIG.agent_name] = CODIGO_CONFIG.persona
    except ImportError:
        pass

    try:
        from apps.agents.funding.config import FUNDING_CONFIG
        if FUNDING_CONFIG.persona is not None:
            registry[FUNDING_CONFIG.agent_name] = FUNDING_CONFIG.persona
    except ImportError:
        pass

    try:
        from apps.agents.mercado.config import MERCADO_CONFIG
        if MERCADO_CONFIG.persona is not None:
            registry[MERCADO_CONFIG.agent_name] = MERCADO_CONFIG.persona
    except ImportError:
        pass

    return registry


def get_agent_persona(agent_name: str) -> Optional[AgentPersona]:
    """Look up the persona for a given agent name.

    Args:
        agent_name: Lowercase agent identifier (e.g., "sintese", "radar").

    Returns:
        The AgentPersona if one is configured, or None.
    """
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry.get(agent_name)


def get_display_name(agent_name: str) -> str:
    """Return the persona display name, falling back to uppercase agent name.

    Convenience helper for bylines: always returns a usable string.

    Args:
        agent_name: Lowercase agent identifier (e.g., "sintese").

    Returns:
        Persona display_name if available, otherwise agent_name.upper().
    """
    persona = get_agent_persona(agent_name)
    if persona is not None:
        return persona.display_name
    return agent_name.upper()
