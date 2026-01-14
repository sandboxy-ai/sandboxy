"""Tests for tool loader module."""

import pytest

from sandboxy.core.state import EnvConfig, ToolRef
from sandboxy.tools.base import BaseTool
from sandboxy.tools.loader import (
    BUILTIN_TOOLS,
    ToolLoader,
    load_tool_class,
)


class TestLoadToolClass:
    """Tests for load_tool_class function."""

    def test_load_base_tool(self) -> None:
        """Test loading the BaseTool class."""
        tool_cls = load_tool_class("sandboxy.tools.base:BaseTool")

        assert tool_cls is not None
        assert tool_cls is BaseTool

    def test_load_invalid_module_raises(self) -> None:
        """Test loading from invalid module raises ImportError."""
        with pytest.raises(ImportError):
            load_tool_class("nonexistent.module:SomeClass")

    def test_load_invalid_class_raises(self) -> None:
        """Test loading invalid class raises AttributeError."""
        with pytest.raises(AttributeError):
            load_tool_class("sandboxy.tools.base:NonexistentClass")


class TestBuiltinTools:
    """Tests for BUILTIN_TOOLS constant."""

    def test_builtin_tools_has_mock_tools(self) -> None:
        """Test that BUILTIN_TOOLS has mock tool mappings."""
        assert isinstance(BUILTIN_TOOLS, dict)
        # Check at least one expected tool
        assert "mock_lemonade" in BUILTIN_TOOLS


class TestToolLoaderFromEnvConfig:
    """Tests for ToolLoader.from_env_config method."""

    def test_raises_for_unknown_tool_type(self) -> None:
        """Test raises ValueError for unknown tool type."""
        env = EnvConfig(
            tools=[
                ToolRef(name="unknown", type="nonexistent_tool_type"),
            ],
            initial_state={},
        )

        with pytest.raises(ValueError, match="Unknown tool type"):
            ToolLoader.from_env_config(env)

    def test_empty_env_returns_empty_dict(self) -> None:
        """Test empty env config returns empty tools dict."""
        env = EnvConfig(tools=[], initial_state={})

        tools = ToolLoader.from_env_config(env)

        assert tools == {}


class TestToolLoaderGetAvailableTools:
    """Tests for ToolLoader.get_available_tools method."""

    def test_returns_list(self) -> None:
        """Test that get_available_tools returns a list."""
        available = ToolLoader.get_available_tools(tool_dirs=[])

        assert isinstance(available, list)

    def test_returns_sorted_list(self) -> None:
        """Test that the list is sorted."""
        available = ToolLoader.get_available_tools(tool_dirs=[])

        assert available == sorted(available)
