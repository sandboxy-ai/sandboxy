"""Root pytest configuration and shared fixtures.

This module provides:
- Pytest configuration and markers
- Environment management fixtures
- Agent testing fixtures (StubAgent, configs)
- Module and tool fixtures
- HTTP mocking fixtures for providers
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sandboxy.agents.base import AgentAction, AgentConfig
from sandboxy.core.state import EnvConfig, EvaluationCheck, Message, ModuleSpec, Step
from sandboxy.tools.base import ToolConfig, ToolResult

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "requires_api_key: marks tests requiring real API keys")


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset environment variables for each test to ensure isolation."""
    # Clear API keys to ensure stub mode by default
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def mock_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock API keys for tests that need them."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_yaml_file(temp_dir: Path) -> Generator[tuple[Path, Any], None, None]:
    """Factory fixture for creating temporary YAML files.

    Returns a tuple of (temp_dir, create_yaml_function).
    """
    created_files: list[Path] = []

    def create_yaml(content: str, filename: str = "test.yml") -> Path:
        path = temp_dir / filename
        path.write_text(content)
        created_files.append(path)
        return path

    return temp_dir, create_yaml


# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a basic agent configuration."""
    return AgentConfig(
        id="test/basic-agent",
        name="Test Agent",
        kind="llm-prompt",
        model="gpt-4o",
        system_prompt="You are a helpful test agent.",
    )


class StubAgent:
    """A stub agent for testing that returns predefined responses.

    Usage:
        agent = StubAgent([
            AgentAction(type="message", content="Hello!"),
            AgentAction(type="tool_call", tool_name="shopify", ...),
        ])
        action = agent.step(history)  # Returns first response
        action = agent.step(history)  # Returns second response
        action = agent.step(history)  # Returns stop (exhausted)
    """

    def __init__(self, responses: list[AgentAction] | None = None) -> None:
        self.config = AgentConfig(
            id="test/stub-agent",
            name="Stub Agent",
            kind="llm-prompt",
        )
        self.responses = responses or [AgentAction(type="message", content="Stub response")]
        self.call_count = 0
        self.received_history: list[list[Message]] = []
        self.received_tools: list[list[dict[str, Any]] | None] = []

    def step(
        self, history: list[Message], available_tools: list[dict[str, Any]] | None = None
    ) -> AgentAction:
        """Process history and return next predefined response."""
        self.received_history.append(list(history))
        self.received_tools.append(available_tools)

        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return AgentAction(type="stop")


@pytest.fixture
def stub_agent() -> type[StubAgent]:
    """Return the StubAgent class for creating stub agents in tests."""
    return StubAgent


# =============================================================================
# Module Fixtures
# =============================================================================


@pytest.fixture
def simple_module_spec() -> ModuleSpec:
    """Create a simple module specification with no tools."""
    return ModuleSpec(
        id="test/simple",
        description="Simple test module",
        environment=EnvConfig(
            sandbox_type="local",
            tools=[],
            initial_state={},
        ),
        steps=[
            Step(id="s1", action="inject_user", params={"content": "Hello"}),
            Step(id="s2", action="await_agent", params={}),
        ],
        evaluation=[],
    )


@pytest.fixture
def module_with_evaluation_spec() -> ModuleSpec:
    """Create a module specification with evaluation checks."""
    return ModuleSpec(
        id="test/with-eval",
        description="Module with evaluation",
        environment=EnvConfig(
            sandbox_type="local",
            tools=[],
            initial_state={},
        ),
        steps=[
            Step(id="s1", action="inject_user", params={"content": "Hello"}),
            Step(id="s2", action="await_agent", params={}),
        ],
        evaluation=[
            EvaluationCheck(
                name="ResponseCheck",
                kind="contains",
                target="agent_messages",
                value="help",
                expected=True,
            ),
        ],
    )


# =============================================================================
# Tool Fixtures
# =============================================================================


@pytest.fixture
def tool_config() -> ToolConfig:
    """Create a basic tool configuration."""
    return ToolConfig(
        name="test_tool",
        type="mock_test",
        description="Test tool",
        config={},
    )


class MockTool:
    """A mock tool for testing that tracks invocations."""

    def __init__(self, config: ToolConfig) -> None:
        self.name = config.name
        self.description = config.description
        self.config = config.config
        self.invocations: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        self._responses: dict[str, ToolResult] = {}

    def set_response(self, action: str, result: ToolResult) -> None:
        """Set a custom response for an action."""
        self._responses[action] = result

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Invoke the tool and record the call."""
        self.invocations.append((action, args.copy(), env_state.copy()))
        if action in self._responses:
            return self._responses[action]
        return ToolResult(success=True, data={"action": action, "args": args})

    def get_actions(self) -> list[dict[str, Any]]:
        """Return mock action definitions."""
        return [
            {"name": "test_action", "description": "Test action", "parameters": {}},
        ]


@pytest.fixture
def mock_tool() -> type[MockTool]:
    """Return the MockTool class for creating mock tools in tests."""
    return MockTool


# =============================================================================
# Message Fixtures
# =============================================================================


@pytest.fixture
def sample_history() -> list[Message]:
    """Create a sample conversation history."""
    return [
        Message(role="user", content="I need help with my order"),
        Message(role="assistant", content="I can help with that. What is your order number?"),
        Message(role="user", content="Order number is ORD123"),
    ]


# =============================================================================
# HTTP Mocking Fixtures
# =============================================================================


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Create a mock httpx response for provider tests."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "gen-123",
        "model": "openai/gpt-4o",
        "choices": [
            {
                "message": {"content": "Test response from mock"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_httpx_client(mock_httpx_response: MagicMock) -> MagicMock:
    """Create a mock httpx client for provider tests."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_httpx_response)
    mock_client.get = AsyncMock(return_value=mock_httpx_response)
    return mock_client


# =============================================================================
# Provider Fixtures
# =============================================================================


@pytest.fixture
def mock_provider_registry():
    """Create a mock provider registry for testing."""
    from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse

    class MockProvider(BaseProvider):
        provider_name = "mock"

        async def complete(
            self,
            model: str,
            messages: list[dict[str, Any]],
            **kwargs: Any,
        ) -> ModelResponse:
            return ModelResponse(
                content="Mock response",
                model_id=model,
                latency_ms=100,
                input_tokens=10,
                output_tokens=20,
                cost_usd=0.001,
            )

        def list_models(self) -> list[ModelInfo]:
            return [
                ModelInfo(
                    id="mock/test-model",
                    name="Mock Test Model",
                    provider="mock",
                    context_length=8192,
                    input_cost_per_million=1.0,
                    output_cost_per_million=2.0,
                )
            ]

    registry = MagicMock()
    registry.get_provider_for_model = MagicMock(return_value=MockProvider())
    registry.providers = {"mock": MockProvider()}
    registry.available_providers = ["mock"]
    registry.list_all_models = MagicMock(return_value=MockProvider().list_models())

    return registry
