"""Tests for the runner engine."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from sandboxy.agents.base import AgentAction, AgentConfig
from sandboxy.agents.llm_prompt import LlmPromptAgent
from sandboxy.core.mdl_parser import load_module
from sandboxy.core.runner import RunEvent, Runner, RunResult
from sandboxy.core.state import Message


class StubAgent:
    """A stub agent for testing that returns predefined responses."""

    def __init__(self, responses: list[AgentAction]) -> None:
        self.config = AgentConfig(
            id="test/stub-agent",
            name="Stub Agent",
            kind="llm-prompt",
        )
        self.responses = responses
        self.call_count = 0

    def step(self, history: list[Message], available_tools: list | None = None) -> AgentAction:
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return AgentAction(type="stop")


class TestRunner:
    """Tests for Runner class."""

    @pytest.fixture
    def simple_module_path(self) -> Generator[Path, None, None]:
        """Create a simple test module."""
        yaml_content = """id: test/simple
description: Simple test module
environment:
  sandbox_type: local
  tools: []
  initial_state: {}
steps:
  - id: s1
    action: inject_user
    params:
      content: Hello
  - id: s2
    action: await_agent
    params: {}
evaluation: []
"""
        fd, path_str = tempfile.mkstemp(suffix=".yml")
        path = Path(path_str)
        path.write_text(yaml_content)
        try:
            yield path
        finally:
            path.unlink(missing_ok=True)

    @pytest.fixture
    def module_with_tools_path(self) -> Generator[Path, None, None]:
        """Create a module with tools."""
        yaml_content = """id: test/with-tools
description: Module with tools
environment:
  sandbox_type: local
  tools:
    - name: shopify
      type: mock_shopify
      description: Mock store
      config: {}
  initial_state:
    cash_balance: 1000.0
steps:
  - id: s1
    action: inject_user
    params:
      content: I need help with order ORD123
  - id: s2
    action: await_agent
    params: {}
evaluation:
  - name: CashCheck
    kind: deterministic
    config:
      expr: "env_state.get('cash_balance', 0) >= 0"
"""
        fd, path_str = tempfile.mkstemp(suffix=".yml")
        path = Path(path_str)
        path.write_text(yaml_content)
        try:
            yield path
        finally:
            path.unlink(missing_ok=True)

    def test_run_simple_module(self, simple_module_path: Path) -> None:
        """Test running a simple module."""
        module = load_module(simple_module_path)
        agent = StubAgent([AgentAction(type="message", content="Hello! How can I help?")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.module_id == "test/simple"
        assert result.agent_id == "test/stub-agent"
        assert len(result.events) >= 2  # At least user + agent

        # Check events
        user_events = [e for e in result.events if e.type == "user"]
        agent_events = [e for e in result.events if e.type == "agent"]
        assert len(user_events) == 1
        assert len(agent_events) == 1
        assert user_events[0].payload["content"] == "Hello"
        assert agent_events[0].payload["content"] == "Hello! How can I help?"

    def test_run_with_tool_call(self, module_with_tools_path: Path) -> None:
        """Test running a module where agent makes tool calls."""
        module = load_module(module_with_tools_path)
        agent = StubAgent([
            AgentAction(
                type="tool_call",
                tool_name="shopify",
                tool_action="get_order",
                tool_args={"order_id": "ORD123"},
            ),
        ])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Check tool call events
        tool_call_events = [e for e in result.events if e.type == "tool_call"]
        tool_result_events = [e for e in result.events if e.type == "tool_result"]

        assert len(tool_call_events) == 1
        assert len(tool_result_events) == 1
        assert tool_call_events[0].payload["tool"] == "shopify"
        assert tool_call_events[0].payload["action"] == "get_order"

    def test_run_with_stop_action(self, simple_module_path: Path) -> None:
        """Test that stop action ends execution."""
        module = load_module(simple_module_path)
        agent = StubAgent([AgentAction(type="stop")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Should have user event but agent stopped
        user_events = [e for e in result.events if e.type == "user"]
        assert len(user_events) == 1

    def test_evaluation_deterministic(self, module_with_tools_path: Path) -> None:
        """Test deterministic evaluation."""
        module = load_module(module_with_tools_path)
        agent = StubAgent([AgentAction(type="message", content="Let me check.")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert "CashCheck" in result.evaluation.checks
        assert result.evaluation.checks["CashCheck"] is True

    def test_env_state_updated_by_tools(self, module_with_tools_path: Path) -> None:
        """Test that tools can update env_state."""
        module = load_module(module_with_tools_path)
        agent = StubAgent([
            AgentAction(
                type="tool_call",
                tool_name="shopify",
                tool_action="refund_order",
                tool_args={"order_id": "ORD123"},
            ),
        ])

        runner = Runner(module=module, agent=agent)
        runner.run()

        # Cash should have been reduced by refund
        assert runner.env_state["cash_balance"] < 1000.0


class TestRunResult:
    """Tests for RunResult."""

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        result = RunResult(
            module_id="test/module",
            agent_id="test/agent",
            events=[RunEvent(type="user", payload={"content": "Hello"})],
        )
        json_str = result.to_json()

        assert "test/module" in json_str
        assert "test/agent" in json_str
        assert "Hello" in json_str

    def test_pretty_format(self) -> None:
        """Test pretty print format."""
        result = RunResult(
            module_id="test/module",
            agent_id="test/agent",
            events=[
                RunEvent(type="user", payload={"content": "Hello"}),
                RunEvent(type="agent", payload={"content": "Hi there!"}),
            ],
        )
        pretty = result.pretty()

        assert "Module: test/module" in pretty
        assert "Agent: test/agent" in pretty
        assert "USER: Hello" in pretty
        assert "AGENT: Hi there!" in pretty


class TestRunnerWithRealAgent:
    """Integration tests with real LlmPromptAgent (stub mode)."""

    @pytest.fixture
    def module_path(self) -> Generator[Path, None, None]:
        """Create test module."""
        yaml_content = """id: test/integration
description: Integration test
environment:
  sandbox_type: local
  tools: []
  initial_state: {}
steps:
  - id: s1
    action: inject_user
    params:
      content: I need help with a refund
  - id: s2
    action: await_agent
    params: {}
evaluation: []
"""
        fd, path_str = tempfile.mkstemp(suffix=".yml")
        path = Path(path_str)
        path.write_text(yaml_content)
        try:
            yield path
        finally:
            path.unlink(missing_ok=True)

    def test_run_with_llm_agent_stub(self, module_path: Path) -> None:
        """Test running with LlmPromptAgent in stub mode."""
        module = load_module(module_path)
        config = AgentConfig(
            id="test/llm-stub",
            name="Test LLM Stub",
            kind="llm-prompt",
            model="gpt-4o",
        )
        agent = LlmPromptAgent(config)

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Should complete with stub response
        assert len(result.events) >= 2
        agent_events = [e for e in result.events if e.type == "agent"]
        assert len(agent_events) == 1
        # Stub should respond about refund
        assert "refund" in agent_events[0].payload["content"].lower()
