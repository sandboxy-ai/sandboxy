"""Tests for agent implementations."""

import tempfile
from pathlib import Path

import pytest

from sandboxy.agents.base import AgentConfig
from sandboxy.agents.llm_prompt import LlmPromptAgent
from sandboxy.agents.loader import AgentLoader, create_agent_from_config
from sandboxy.core.state import Message


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_create_config(self) -> None:
        """Test creating an agent config."""
        config = AgentConfig(
            id="test/agent",
            name="Test Agent",
            kind="llm-prompt",
            model="gpt-4o",
            system_prompt="You are a test agent.",
            tools=["shopify"],
            params={"temperature": 0.5},
        )
        assert config.id == "test/agent"
        assert config.kind == "llm-prompt"
        assert config.model == "gpt-4o"
        assert len(config.tools) == 1


class TestLlmPromptAgent:
    """Tests for LlmPromptAgent."""

    @pytest.fixture
    def agent(self) -> LlmPromptAgent:
        """Create an LlmPromptAgent instance without API key."""
        config = AgentConfig(
            id="test/llm-agent",
            name="Test LLM Agent",
            kind="llm-prompt",
            model="gpt-4o",
            system_prompt="You are a helpful support agent.",
        )
        return LlmPromptAgent(config)

    def test_stub_response_without_api_key(self, agent: LlmPromptAgent) -> None:
        """Test that agent returns stub response without API key."""
        history = [Message(role="user", content="Hello, I need help")]
        action = agent.step(history)

        assert action.type == "message"
        assert action.content is not None
        assert "STUB" in action.content or "stub" in action.content.lower()

    def test_stub_response_for_refund(self, agent: LlmPromptAgent) -> None:
        """Test contextual stub response for refund queries."""
        history = [Message(role="user", content="I need a refund for my order")]
        action = agent.step(history)

        assert action.type == "message"
        assert action.content is not None
        # Should mention refund in contextual stub
        assert "refund" in action.content.lower()

    def test_stub_response_for_order(self, agent: LlmPromptAgent) -> None:
        """Test contextual stub response for order queries."""
        history = [Message(role="user", content="Where is my order?")]
        action = agent.step(history)

        assert action.type == "message"
        assert action.content is not None
        assert "order" in action.content.lower()

    def test_config_accessible(self, agent: LlmPromptAgent) -> None:
        """Test that agent config is accessible."""
        assert agent.config.id == "test/llm-agent"
        assert agent.config.kind == "llm-prompt"


class TestAgentLoader:
    """Tests for AgentLoader."""

    @pytest.fixture
    def temp_agent_dir(self) -> Path:
        """Create a temporary directory with agent configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "agents"
            agent_dir.mkdir()

            # Create test agent config
            agent_yaml = """
id: test/loader-agent
name: Loader Test Agent
kind: llm-prompt
model: gpt-3.5-turbo
system_prompt: Test prompt
tools:
  - shopify
params:
  temperature: 0.5
"""
            (agent_dir / "test_agent.yaml").write_text(agent_yaml)

            yield agent_dir

    def test_load_agents_from_dir(self, temp_agent_dir: Path) -> None:
        """Test loading agents from directory."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        agent_ids = loader.list_ids()

        assert len(agent_ids) == 1
        assert "test/loader-agent" in agent_ids

    def test_load_specific_agent(self, temp_agent_dir: Path) -> None:
        """Test loading a specific agent by ID."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        agent = loader.load("test/loader-agent")

        assert agent.config.id == "test/loader-agent"
        assert agent.config.name == "Loader Test Agent"

    def test_load_nonexistent_agent(self, temp_agent_dir: Path) -> None:
        """Test loading nonexistent agent raises error."""
        loader = AgentLoader(dirs=[temp_agent_dir])

        with pytest.raises(ValueError, match="Agent not found"):
            loader.load("nonexistent/agent")

    def test_get_config(self, temp_agent_dir: Path) -> None:
        """Test getting agent config without instantiating."""
        loader = AgentLoader(dirs=[temp_agent_dir])
        config = loader.get_config("test/loader-agent")

        assert config is not None
        assert config.model == "gpt-3.5-turbo"

    def test_load_default_no_agents(self) -> None:
        """Test loading default with no agents raises error."""
        loader = AgentLoader(dirs=[])

        with pytest.raises(ValueError, match="No agents available"):
            loader.load_default()


class TestCreateAgentFromConfig:
    """Tests for create_agent_from_config helper."""

    def test_create_llm_prompt_agent(self) -> None:
        """Test creating LLM prompt agent from config."""
        config = AgentConfig(
            id="direct/agent",
            name="Direct Agent",
            kind="llm-prompt",
            model="gpt-4o",
        )
        agent = create_agent_from_config(config)

        assert isinstance(agent, LlmPromptAgent)
        assert agent.config.id == "direct/agent"

    def test_create_unsupported_kind(self) -> None:
        """Test creating agent with unsupported kind raises error."""
        config = AgentConfig(
            id="unsupported/agent",
            name="Unsupported Agent",
            kind="python-module",  # Not yet implemented
        )

        with pytest.raises(ValueError, match="Unsupported agent kind"):
            create_agent_from_config(config)
