"""Base configuration for Sinal.lab agents.

Each agent subclass defines its own config with data sources,
parameters, and scheduling. This module provides the base structure.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DataSourceConfig:
    """Configuration for a single data source."""

    name: str
    source_type: str  # api, rss, scraper, file
    url: Optional[str] = None
    api_key_env: Optional[str] = None  # environment variable name for API key
    rate_limit_per_minute: int = 60
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Base configuration shared by all agents."""

    agent_name: str
    version: str = "0.1.0"
    description: str = ""
    data_sources: list[DataSourceConfig] = field(default_factory=list)
    schedule_cron: Optional[str] = None  # e.g., "0 8 * * 1" for weekly Monday 8am
    output_content_type: str = "DATA_REPORT"
    min_confidence_to_publish: float = 0.3
    max_items_per_run: int = 1000

    def get_enabled_sources(self) -> list[DataSourceConfig]:
        """Return only enabled data sources."""
        return [s for s in self.data_sources if s.enabled]

    def get_source_by_name(self, name: str) -> Optional[DataSourceConfig]:
        """Look up a data source by name."""
        for source in self.data_sources:
            if source.name == name:
                return source
        return None
