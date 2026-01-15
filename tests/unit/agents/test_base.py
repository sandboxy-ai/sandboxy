"""Tests for agent base module."""

from sandboxy.agents.base import AgentAction, AgentConfig, BaseAgent
from sandboxy.core.state import Message
from tests.factories import AgentConfigFactory


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_create_basic_config(self) -> None:
        """Test creating a basic agent config."""
        config = AgentConfig(
            id="test/agent",
            name="Test Agent",
            kind="llm-prompt",
        )
        assert config.id == "test/agent"
        assert config.name == "Test Agent"
        assert config.kind == "llm-prompt"

    def test_create_full_config(self) -> None:
        """Test creating a full agent config."""
        config = AgentConfig(
            id="test/full",
            name="Full Agent",
            kind="llm-prompt",
            model="gpt-4o",
            system_prompt="You are helpful.",
            tools=["shopify", "email"],
            params={"temperature": 0.5},
        )
        assert config.model == "gpt-4o"
        assert config.system_prompt == "You are helpful."
        assert len(config.tools) == 2
        assert config.params["temperature"] == 0.5

    def test_config_defaults(self) -> None:
        """Test agent config default values."""
        config = AgentConfig(
            id="test/defaults",
            name="Default Agent",
            kind="llm-prompt",
        )
        assert config.model == ""
        assert config.system_prompt == ""
        assert config.tools == []
        assert config.params == {}
        assert config.impl == {}

    def test_config_serialization(self) -> None:
        """Test config serializes to dict."""
        config = AgentConfig(
            id="test/serial",
            name="Serial Agent",
            kind="llm-prompt",
            model="gpt-4o",
        )
        data = config.model_dump()
        assert data["id"] == "test/serial"
        assert data["model"] == "gpt-4o"

    def test_factory_creates_valid_config(self) -> None:
        """Test factory creates valid configuration."""
        config = AgentConfigFactory.create()
        assert config.id.startswith("test/")
        assert config.kind == "llm-prompt"


class TestAgentAction:
    """Tests for AgentAction model."""

    def test_create_message_action(self) -> None:
        """Test creating a message action."""
        action = AgentAction(type="message", content="Hello!")
        assert action.type == "message"
        assert action.content == "Hello!"
        assert action.tool_name is None

    def test_create_tool_call_action(self) -> None:
        """Test creating a tool call action."""
        action = AgentAction(
            type="tool_call",
            tool_name="shopify",
            tool_action="get_order",
            tool_args={"order_id": "123"},
            tool_call_id="call_abc",
        )
        assert action.type == "tool_call"
        assert action.tool_name == "shopify"
        assert action.tool_action == "get_order"
        assert action.tool_args["order_id"] == "123"
        assert action.tool_call_id == "call_abc"

    def test_create_stop_action(self) -> None:
        """Test creating a stop action."""
        action = AgentAction(type="stop")
        assert action.type == "stop"
        assert action.content is None

    def test_action_serialization(self) -> None:
        """Test action serializes to dict."""
        action = AgentAction(type="message", content="Test")
        data = action.model_dump()
        assert data["type"] == "message"
        assert data["content"] == "Test"


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_create_base_agent(self) -> None:
        """Test creating a base agent."""
        config = AgentConfigFactory.create()
        agent = BaseAgent(config)
        assert agent.config == config

    def test_base_agent_step_returns_stop(self) -> None:
        """Test base agent step returns stop action by default."""
        config = AgentConfigFactory.create()
        agent = BaseAgent(config)

        history = [Message(role="user", content="Hello")]
        action = agent.step(history)

        assert action.type == "stop"

    def test_base_agent_step_with_tools(self) -> None:
        """Test base agent step accepts tools parameter."""
        config = AgentConfigFactory.create()
        agent = BaseAgent(config)

        history = [Message(role="user", content="Hello")]
        tools = [{"name": "test", "description": "Test tool"}]
        action = agent.step(history, tools)

        assert action.type == "stop"

    def test_base_agent_config_accessible(self) -> None:
        """Test agent config is accessible."""
        config = AgentConfigFactory.create(
            id="test/accessible",
            model="gpt-4o",
        )
        agent = BaseAgent(config)

        assert agent.config.id == "test/accessible"
        assert agent.config.model == "gpt-4o"


class TestAgentConfigFactory:
    """Tests for AgentConfigFactory."""

    def test_factory_increments_counter(self) -> None:
        """Test factory creates unique IDs."""
        AgentConfigFactory.reset_counter()
        config1 = AgentConfigFactory.create()
        config2 = AgentConfigFactory.create()
        assert config1.id != config2.id

    def test_factory_accepts_custom_values(self) -> None:
        """Test factory accepts custom values."""
        config = AgentConfigFactory.create(
            id="custom/id",
            name="Custom Name",
            model="custom-model",
            system_prompt="Custom prompt",
        )
        assert config.id == "custom/id"
        assert config.name == "Custom Name"
        assert config.model == "custom-model"
        assert config.system_prompt == "Custom prompt"

    def test_factory_reset(self) -> None:
        """Test factory counter reset."""
        AgentConfigFactory.reset_counter()
        config1 = AgentConfigFactory.create()
        AgentConfigFactory.reset_counter()
        config2 = AgentConfigFactory.create()
        # After reset, should get same suffix
        assert config1.id.split("-")[-1] == config2.id.split("-")[-1]
