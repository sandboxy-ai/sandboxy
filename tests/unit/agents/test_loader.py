"""Tests for agent loader module."""

from pathlib import Path

import pytest

from sandboxy.agents.base import AgentConfig
from sandboxy.agents.loader import AgentLoader, create_agent_from_config


class TestAgentLoader:
    """Tests for AgentLoader class."""

    @pytest.fixture
    def temp_agent_dir(self, tmp_path: Path) -> Path:
        """Create a temp directory with agent YAML files."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create a valid agent YAML
        valid_yaml = agent_dir / "test_agent.yaml"
        valid_yaml.write_text("""
id: test/valid-agent
name: Valid Test Agent
kind: llm-prompt
model: openai/gpt-4o
system_prompt: You are helpful.
tools:
  - shopify
params:
  temperature: 0.5
""")

        # Create another agent
        another_yaml = agent_dir / "another.yml"
        another_yaml.write_text("""
id: test/another-agent
name: Another Agent
kind: llm-prompt
model: anthropic/claude-3.5-sonnet
""")

        # Create an invalid YAML (missing id)
        invalid_yaml = agent_dir / "invalid.yaml"
        invalid_yaml.write_text("""
name: Invalid Agent
kind: llm-prompt
""")

        return agent_dir

    def test_loader_finds_yaml_files(self, temp_agent_dir: Path) -> None:
        """Test that loader finds .yaml and .yml files."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        ids = loader.list_ids()

        assert "test/valid-agent" in ids
        assert "test/another-agent" in ids

    def test_loader_skips_invalid_files(self, temp_agent_dir: Path) -> None:
        """Test that loader skips files without id."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        ids = loader.list_ids()

        # Should not include invalid agent (no id)
        assert len(ids) == 2

    def test_get_config_returns_config(self, temp_agent_dir: Path) -> None:
        """Test getting a config by ID."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        config = loader.get_config("test/valid-agent")

        assert config is not None
        assert config.id == "test/valid-agent"
        assert config.name == "Valid Test Agent"
        assert config.model == "openai/gpt-4o"
        assert config.system_prompt == "You are helpful."
        assert "shopify" in config.tools
        assert config.params["temperature"] == 0.5

    def test_get_config_returns_none_for_missing(self, temp_agent_dir: Path) -> None:
        """Test that get_config returns None for unknown ID."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        config = loader.get_config("nonexistent/agent")

        assert config is None

    def test_load_returns_agent_instance(self, temp_agent_dir: Path) -> None:
        """Test that load returns an agent instance."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        agent = loader.load("test/valid-agent")

        assert agent is not None
        assert agent.config.id == "test/valid-agent"

    def test_load_raises_for_unknown_id(self, temp_agent_dir: Path) -> None:
        """Test that load raises ValueError for unknown ID."""
        loader = AgentLoader(dirs=[temp_agent_dir])

        with pytest.raises(ValueError, match="Agent not found"):
            loader.load("nonexistent-agent")

    def test_load_creates_dynamic_agent_for_model_ids(self, temp_agent_dir: Path) -> None:
        """Test that load creates a dynamic agent for model IDs with slashes."""
        loader = AgentLoader(dirs=[temp_agent_dir])

        # Model IDs with "/" are treated as ad-hoc model references
        agent = loader.load("google/gemini-2.0-flash")
        assert agent is not None
        assert agent.config.id == "google/gemini-2.0-flash"
        assert agent.config.model == "google/gemini-2.0-flash"

    def test_loader_handles_empty_directory(self, tmp_path: Path) -> None:
        """Test loader handles empty directories gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = AgentLoader(dirs=[empty_dir])

        assert loader.list_ids() == []

    def test_loader_handles_nonexistent_directory(self) -> None:
        """Test loader handles nonexistent directories gracefully."""
        loader = AgentLoader(dirs=[Path("/nonexistent/path")])

        assert loader.list_ids() == []

    def test_loader_handles_malformed_yaml(self, tmp_path: Path) -> None:
        """Test loader handles malformed YAML gracefully."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        malformed = agent_dir / "malformed.yaml"
        malformed.write_text("this: is: not: valid: yaml: [")

        loader = AgentLoader(dirs=[agent_dir])

        # Should not raise, just skip the file
        assert loader.list_ids() == []

    def test_config_defaults_applied(self, tmp_path: Path) -> None:
        """Test that config defaults are applied for missing fields."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        minimal = agent_dir / "minimal.yaml"
        minimal.write_text("""
id: test/minimal
""")

        loader = AgentLoader(dirs=[agent_dir])
        config = loader.get_config("test/minimal")

        assert config is not None
        assert config.name == "test/minimal"  # Defaults to id
        assert config.kind == "llm-prompt"  # Default kind
        assert config.model == ""
        assert config.system_prompt == ""
        assert config.tools == []
        assert config.params == {}


class TestAgentLoaderLoadDefault:
    """Tests for load_default method."""

    def test_load_default_raises_when_no_agents(self) -> None:
        """Test load_default raises when no agents available."""
        loader = AgentLoader(dirs=[])

        with pytest.raises(ValueError, match="No agents available"):
            loader.load_default()

    def test_load_default_returns_first_available(self, tmp_path: Path) -> None:
        """Test load_default returns an agent when available."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        agent_yaml = agent_dir / "test.yaml"
        agent_yaml.write_text("""
id: test/default-test
name: Default Test
kind: llm-prompt
""")

        loader = AgentLoader(dirs=[agent_dir])
        agent = loader.load_default()

        assert agent is not None


class TestCreateAgentFromConfig:
    """Tests for create_agent_from_config function."""

    def test_creates_llm_prompt_agent(self) -> None:
        """Test creating an LlmPromptAgent from config."""
        config = AgentConfig(
            id="test/config-agent",
            name="Config Agent",
            kind="llm-prompt",
            model="openai/gpt-4o",
        )

        agent = create_agent_from_config(config)

        assert agent is not None
        assert agent.config == config

    def test_raises_for_unimplemented_kind(self) -> None:
        """Test raises ValueError for valid but unimplemented agent kind.

        AgentConfig.kind is a Literal type, so Pydantic validates the values.
        But some valid kinds (like 'python-module') may not be implemented yet.
        """
        config = AgentConfig(
            id="test/unimplemented",
            name="Unimplemented Agent",
            kind="python-module",  # Valid Literal value but not implemented
        )

        with pytest.raises(ValueError, match="Unsupported agent kind"):
            create_agent_from_config(config)
