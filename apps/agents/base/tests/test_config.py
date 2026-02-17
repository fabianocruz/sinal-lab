"""Tests for AgentConfig and AgentCategory."""

import pytest
from apps.agents.base.config import AgentCategory, AgentConfig, DataSourceConfig


class TestAgentCategory:
    """Test suite for AgentCategory enum."""

    def test_enum_values_exist(self):
        """All three categories exist with correct string values."""
        assert AgentCategory.DATA == "data"
        assert AgentCategory.CONTENT == "content"
        assert AgentCategory.QUALITY == "quality"

    def test_is_str_enum(self):
        """AgentCategory inherits from str for serialization."""
        assert isinstance(AgentCategory.DATA, str)
        assert isinstance(AgentCategory.CONTENT, str)
        assert isinstance(AgentCategory.QUALITY, str)

    def test_enum_membership(self):
        """Test that values work with 'in' checks."""
        values = [c.value for c in AgentCategory]
        assert "data" in values
        assert "content" in values
        assert "quality" in values

    def test_enum_count(self):
        """Only three categories exist."""
        assert len(AgentCategory) == 3


class TestAgentConfigCategory:
    """Test suite for agent_category field on AgentConfig."""

    def test_default_category_is_content(self):
        """Default category is CONTENT for backward compatibility."""
        config = AgentConfig(agent_name="test")
        assert config.agent_category == AgentCategory.CONTENT

    def test_explicit_data_category(self):
        """Can set DATA category explicitly."""
        config = AgentConfig(agent_name="funding", agent_category=AgentCategory.DATA)
        assert config.agent_category == AgentCategory.DATA

    def test_explicit_quality_category(self):
        """Can set QUALITY category explicitly."""
        config = AgentConfig(agent_name="editorial", agent_category=AgentCategory.QUALITY)
        assert config.agent_category == AgentCategory.QUALITY

    def test_category_preserved_with_other_fields(self):
        """Category works alongside all other AgentConfig fields."""
        config = AgentConfig(
            agent_name="mercado",
            version="0.2.0",
            description="Market Intelligence",
            agent_category=AgentCategory.DATA,
            output_content_type="DATA_REPORT",
            max_items_per_run=500,
        )
        assert config.agent_category == AgentCategory.DATA
        assert config.agent_name == "mercado"
        assert config.version == "0.2.0"


class TestAgentConfigExisting:
    """Regression tests — ensure existing AgentConfig behavior is unchanged."""

    def test_create_minimal_config(self):
        """Minimal config still works (backward compat)."""
        config = AgentConfig(agent_name="test")
        assert config.agent_name == "test"
        assert config.version == "0.1.0"
        assert config.output_content_type == "DATA_REPORT"
        assert config.min_confidence_to_publish == 0.3
        assert config.max_items_per_run == 1000

    def test_get_enabled_sources(self):
        """get_enabled_sources still works."""
        config = AgentConfig(
            agent_name="test",
            data_sources=[
                DataSourceConfig(name="a", source_type="rss", enabled=True),
                DataSourceConfig(name="b", source_type="rss", enabled=False),
            ],
        )
        enabled = config.get_enabled_sources()
        assert len(enabled) == 1
        assert enabled[0].name == "a"

    def test_get_source_by_name(self):
        """get_source_by_name still works."""
        config = AgentConfig(
            agent_name="test",
            data_sources=[
                DataSourceConfig(name="src1", source_type="api"),
            ],
        )
        assert config.get_source_by_name("src1") is not None
        assert config.get_source_by_name("nonexistent") is None
