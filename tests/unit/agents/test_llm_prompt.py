"""Tests for LlmPromptAgent."""

from unittest.mock import MagicMock, patch

import pytest

from sandboxy.agents.base import AgentConfig
from sandboxy.agents.llm_prompt import LlmPromptAgent
from sandboxy.core.state import Message, ToolCall


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a basic agent config."""
    return AgentConfig(
        id="test/llm-agent",
        name="Test LLM Agent",
        kind="llm-prompt",
        model="openai/gpt-4o",
        system_prompt="You are a helpful assistant.",
        tools=[],
        params={"temperature": 0.7, "max_tokens": 1024},
    )


@pytest.fixture
def agent(agent_config: AgentConfig, monkeypatch: pytest.MonkeyPatch) -> LlmPromptAgent:
    """Create an LlmPromptAgent with mocked API key."""
    # Model contains "/" so it uses OpenRouter, need OPENROUTER_API_KEY
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    return LlmPromptAgent(agent_config)


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """Create a mock OpenAI response with a message."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello! How can I help you?"
    response.choices[0].message.tool_calls = None
    response.choices[0].finish_reason = "stop"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 50
    response.usage.completion_tokens = 20
    return response


class TestLlmPromptAgentInit:
    """Tests for LlmPromptAgent initialization."""

    def test_initializes_with_config(self) -> None:
        """Test that agent initializes with config."""
        config = AgentConfig(
            id="test/agent",
            name="Test",
            kind="llm-prompt",
            model="gpt-4o",
        )
        agent = LlmPromptAgent(config)

        assert agent.config == config
        assert agent.api_key == ""  # No env var set


class TestLlmPromptAgentApiKey:
    """Tests for API key handling."""

    def test_uses_openai_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that OPENAI_API_KEY is used."""
        monkeypatch.setenv("OPENAI_API_KEY", "oai-key")

        config = AgentConfig(
            id="test/oai",
            name="Test",
            kind="llm-prompt",
            model="gpt-4o",
        )
        agent = LlmPromptAgent(config)

        assert agent.api_key == "oai-key"


class TestLlmPromptAgentStubResponse:
    """Tests for stub response when no API key."""

    def test_returns_stub_when_no_api_key(
        self, agent_config: AgentConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that stub response is returned without API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        agent = LlmPromptAgent(agent_config)
        history = [Message(role="user", content="Hello")]

        action = agent.step(history)

        assert action.type == "message"
        assert "[STUB]" in action.content

    def test_stub_responds_to_refund_keyword(
        self, agent_config: AgentConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test stub gives contextual response for refund."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        agent = LlmPromptAgent(agent_config)
        history = [Message(role="user", content="I want a refund please")]

        action = agent.step(history)

        assert action.type == "message"
        assert "refund" in action.content.lower()

    def test_stub_responds_to_order_keyword(
        self, agent_config: AgentConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test stub gives contextual response for order."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        agent = LlmPromptAgent(agent_config)
        history = [Message(role="user", content="Where is my order?")]

        action = agent.step(history)

        assert action.type == "message"
        assert "order" in action.content.lower()


class TestLlmPromptAgentStep:
    """Tests for step method with mocked API."""

    def test_step_returns_message_action(
        self, agent: LlmPromptAgent, mock_openai_response: MagicMock
    ) -> None:
        """Test step returns message action for text response."""
        with patch.object(agent, "_call_api", return_value=mock_openai_response):
            history = [Message(role="user", content="Hello")]
            action = agent.step(history)

            assert action.type == "message"
            assert action.content == "Hello! How can I help you?"

    def test_step_returns_tool_call_action(self, agent: LlmPromptAgent) -> None:
        """Test step returns tool_call action when model calls a tool."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.choices[0].message.tool_calls = [MagicMock()]
        response.choices[0].message.tool_calls[0].id = "call_123"
        response.choices[0].message.tool_calls[0].function.name = "shopify__get_order"
        response.choices[0].message.tool_calls[0].function.arguments = '{"order_id": "ORD123"}'
        response.choices[0].finish_reason = "tool_calls"
        response.usage = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 30

        with patch.object(agent, "_call_api", return_value=response):
            history = [Message(role="user", content="Get order ORD123")]
            action = agent.step(history)

            assert action.type == "tool_call"
            assert action.tool_name == "shopify"
            assert action.tool_action == "get_order"
            assert action.tool_args == {"order_id": "ORD123"}

    def test_step_returns_stop_action(self, agent: LlmPromptAgent) -> None:
        """Test step returns stop action when model stops without content."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.choices[0].message.tool_calls = None
        response.choices[0].finish_reason = "stop"
        response.usage = None

        with patch.object(agent, "_call_api", return_value=response):
            history = [Message(role="user", content="Done")]
            action = agent.step(history)

            assert action.type == "stop"

    def test_step_handles_empty_choices(self, agent: LlmPromptAgent) -> None:
        """Test step handles response with no choices."""
        response = MagicMock()
        response.choices = []
        response.usage = None

        with patch.object(agent, "_call_api", return_value=response):
            history = [Message(role="user", content="Hello")]
            action = agent.step(history)

            assert action.type == "message"
            assert "Error" in action.content


class TestLlmPromptAgentBuildMessages:
    """Tests for _build_messages method."""

    def test_includes_system_prompt(self, agent: LlmPromptAgent) -> None:
        """Test that system prompt is included."""
        history = [Message(role="user", content="Hello")]

        messages = agent._build_messages(history)

        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

    def test_converts_user_messages(self, agent: LlmPromptAgent) -> None:
        """Test that user messages are converted."""
        history = [Message(role="user", content="Hello")]

        messages = agent._build_messages(history)

        # System message + user message
        assert len(messages) == 2
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    def test_converts_assistant_messages(self, agent: LlmPromptAgent) -> None:
        """Test that assistant messages are converted."""
        history = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello!"),
        ]

        messages = agent._build_messages(history)

        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hello!"

    def test_converts_tool_messages(self, agent: LlmPromptAgent) -> None:
        """Test that tool result messages are converted."""
        history = [
            Message(
                role="tool",
                content='{"order_id": "123"}',
                tool_call_id="call_abc",
                tool_name="shopify",
            ),
        ]

        messages = agent._build_messages(history)

        # System + tool
        assert messages[1]["role"] == "tool"
        assert messages[1]["content"] == '{"order_id": "123"}'
        assert messages[1]["tool_call_id"] == "call_abc"

    def test_converts_assistant_with_tool_calls(self, agent: LlmPromptAgent) -> None:
        """Test that assistant messages with tool calls are converted."""
        history = [
            Message(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        name="shopify__get_order",
                        arguments='{"order_id": "ORD123"}',
                    )
                ],
            ),
        ]

        messages = agent._build_messages(history)

        assert messages[1]["role"] == "assistant"
        assert len(messages[1]["tool_calls"]) == 1
        assert messages[1]["tool_calls"][0]["id"] == "call_123"
        assert messages[1]["tool_calls"][0]["function"]["name"] == "shopify__get_order"


class TestLlmPromptAgentBuildTools:
    """Tests for _build_tools method."""

    def test_converts_tools_to_openai_format(self, agent: LlmPromptAgent) -> None:
        """Test that tools are converted to OpenAI format."""
        available_tools = [
            {
                "name": "shopify",
                "description": "Shopify store",
                "actions": [
                    {
                        "name": "get_order",
                        "description": "Get an order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "order_id": {"type": "string"},
                            },
                            "required": ["order_id"],
                        },
                    },
                ],
            },
        ]

        tools = agent._build_tools(available_tools)

        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "shopify__get_order"
        assert tools[0]["function"]["description"] == "Get an order"

    def test_flattens_multiple_actions(self, agent: LlmPromptAgent) -> None:
        """Test that multiple actions are flattened."""
        available_tools = [
            {
                "name": "shopify",
                "description": "Store",
                "actions": [
                    {"name": "get_order", "description": "Get order"},
                    {"name": "refund_order", "description": "Refund order"},
                ],
            },
        ]

        tools = agent._build_tools(available_tools)

        assert len(tools) == 2
        assert tools[0]["function"]["name"] == "shopify__get_order"
        assert tools[1]["function"]["name"] == "shopify__refund_order"


class TestLlmPromptAgentParseResponse:
    """Tests for _parse_response method."""

    def test_handles_legacy_tool_name_format(self, agent: LlmPromptAgent) -> None:
        """Test parsing tool call with single underscore (legacy format).

        The legacy format splits by last underscore, so 'tool_action' becomes
        ('tool', 'action'). More complex names like 'shopify_get_order' become
        ('shopify_get', 'order').
        """
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.choices[0].message.tool_calls = [MagicMock()]
        response.choices[0].message.tool_calls[0].id = "call_123"
        response.choices[0].message.tool_calls[
            0
        ].function.name = "shopify_refund"  # Single underscore
        response.choices[0].message.tool_calls[0].function.arguments = '{"order_id": "123"}'
        response.choices[0].finish_reason = "tool_calls"

        action = agent._parse_response(response)

        # Legacy fallback splits by last underscore
        assert action.type == "tool_call"
        assert action.tool_name == "shopify"
        assert action.tool_action == "refund"

    def test_handles_invalid_json_arguments(self, agent: LlmPromptAgent) -> None:
        """Test handling of invalid JSON in tool arguments."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.choices[0].message.tool_calls = [MagicMock()]
        response.choices[0].message.tool_calls[0].id = "call_123"
        response.choices[0].message.tool_calls[0].function.name = "shopify__get_order"
        response.choices[0].message.tool_calls[0].function.arguments = "not valid json"
        response.choices[0].finish_reason = "tool_calls"

        action = agent._parse_response(response)

        assert action.type == "tool_call"
        assert action.tool_args == {}  # Defaults to empty dict
