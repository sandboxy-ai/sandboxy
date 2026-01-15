"""Tests for the synchronous Runner engine."""

from unittest.mock import MagicMock, patch

import pytest

from sandboxy.core.mdl_parser import load_module
from sandboxy.core.runner import RunEvent, Runner, RunResult
from sandboxy.core.state import (
    ScoringConfig,
)
from sandboxy.tools.base import ToolResult
from tests.conftest import StubAgent
from tests.factories import (
    AgentActionFactory,
    EvaluationCheckFactory,
    ModuleSpecFactory,
    StepFactory,
)


@pytest.fixture
def mock_shopify_tool() -> MagicMock:
    """Create a mock shopify tool for testing."""
    tool = MagicMock()
    tool.name = "shopify"
    tool.description = "Mock Shopify store"
    tool.get_actions.return_value = [
        {"name": "get_order", "description": "Get order details", "parameters": {}},
        {"name": "list_orders", "description": "List all orders", "parameters": {}},
        {"name": "refund_order", "description": "Process refund", "parameters": {}},
    ]

    def mock_invoke(action: str, args: dict, env_state: dict) -> ToolResult:
        if action == "refund_order":
            # Simulate refund reducing balance
            env_state["cash_balance"] = env_state.get("cash_balance", 1000.0) - 50.0
            return ToolResult(success=True, data={"refunded": True, "amount": 50.0})
        return ToolResult(
            success=True,
            data={
                "order_id": args.get("order_id", "ORD123"),
                "status": "completed",
                "total": 99.99,
            },
        )

    tool.invoke.side_effect = mock_invoke
    return tool


class TestRunner:
    """Tests for Runner class."""

    def test_run_simple_module(self, stub_agent: type[StubAgent]) -> None:
        """Test running a simple module with no tools."""
        module = ModuleSpecFactory.create()
        agent = stub_agent([AgentActionFactory.message("Hello! How can I help?")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.module_id == module.id
        assert result.agent_id == agent.config.id
        assert len(result.events) >= 2  # At least user + agent

        # Check events
        user_events = [e for e in result.events if e.type == "user"]
        agent_events = [e for e in result.events if e.type == "agent"]
        assert len(user_events) == 1
        assert len(agent_events) == 1
        assert user_events[0].payload["content"] == "Test message"
        assert agent_events[0].payload["content"] == "Hello! How can I help?"

    def test_run_module_with_custom_steps(self, stub_agent: type[StubAgent]) -> None:
        """Test running a module with custom steps."""
        steps = [
            StepFactory.inject_user("First message"),
            StepFactory.await_agent(),
            StepFactory.inject_user("Second message"),
            StepFactory.await_agent(),
        ]
        module = ModuleSpecFactory.create(steps=steps)
        agent = stub_agent(
            [
                AgentActionFactory.message("First response"),
                AgentActionFactory.message("Second response"),
            ]
        )

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        user_events = [e for e in result.events if e.type == "user"]
        agent_events = [e for e in result.events if e.type == "agent"]
        assert len(user_events) == 2
        assert len(agent_events) == 2

    def test_run_with_tool_call(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test running a module where agent makes tool calls."""
        module = ModuleSpecFactory.with_shopify_tool()
        agent = stub_agent(
            [
                AgentActionFactory.tool_call("shopify", "get_order", {"order_id": "ORD123"}),
                AgentActionFactory.message("I found your order."),
            ]
        )

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            result = runner.run()

        # Check tool call events
        tool_call_events = [e for e in result.events if e.type == "tool_call"]
        tool_result_events = [e for e in result.events if e.type == "tool_result"]

        assert len(tool_call_events) == 1
        assert len(tool_result_events) == 1
        assert tool_call_events[0].payload["tool"] == "shopify"
        assert tool_call_events[0].payload["action"] == "get_order"

    def test_run_with_multiple_tool_calls(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test agent making multiple tool calls before responding."""
        module = ModuleSpecFactory.with_shopify_tool()
        agent = stub_agent(
            [
                AgentActionFactory.tool_call("shopify", "get_order", {"order_id": "ORD123"}),
                AgentActionFactory.tool_call("shopify", "list_orders", {}),
                AgentActionFactory.message("Here's the information."),
            ]
        )

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            result = runner.run()

        tool_call_events = [e for e in result.events if e.type == "tool_call"]
        assert len(tool_call_events) == 2

    def test_stop_action_ends_execution(self, stub_agent: type[StubAgent]) -> None:
        """Test that stop action ends execution immediately."""
        module = ModuleSpecFactory.create()
        agent = stub_agent([AgentActionFactory.stop()])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Should have user event but no agent response
        user_events = [e for e in result.events if e.type == "user"]
        agent_events = [e for e in result.events if e.type == "agent"]
        assert len(user_events) == 1
        assert len(agent_events) == 0

    def test_tool_not_found(self, stub_agent: type[StubAgent]) -> None:
        """Test calling a tool that doesn't exist."""
        module = ModuleSpecFactory.create()  # No tools
        agent = stub_agent(
            [
                AgentActionFactory.tool_call("nonexistent", "action", {}),
                AgentActionFactory.message("Tool not found."),
            ]
        )

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        tool_result_events = [e for e in result.events if e.type == "tool_result"]
        assert len(tool_result_events) == 1
        assert tool_result_events[0].payload["result"]["success"] is False
        assert "not found" in tool_result_events[0].payload["result"]["error"].lower()

    def test_env_state_updated_by_tools(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test that tools can update env_state."""
        module = ModuleSpecFactory.with_shopify_tool(initial_balance=1000.0)
        agent = stub_agent(
            [
                AgentActionFactory.tool_call("shopify", "refund_order", {"order_id": "ORD123"}),
                AgentActionFactory.message("Refund processed."),
            ]
        )

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            runner.run()

            # Cash should have been reduced by refund
            assert runner.env_state["cash_balance"] < 1000.0

    def test_history_contains_tool_messages(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test that tool calls are properly added to history."""
        module = ModuleSpecFactory.with_shopify_tool()
        agent = stub_agent(
            [
                AgentActionFactory.tool_call("shopify", "get_order", {"order_id": "ORD123"}),
                AgentActionFactory.message("Done."),
            ]
        )

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            runner.run()

        # History should contain: user, assistant (tool call), tool (result), assistant (message)
        tool_messages = [m for m in runner.history if m.role == "tool"]
        assert len(tool_messages) >= 1
        assert tool_messages[0].tool_name == "shopify"


class TestRunnerBranching:
    """Tests for branching functionality."""

    def test_branch_to_existing_branch(self, stub_agent: type[StubAgent]) -> None:
        """Test branching to an existing branch."""
        steps = [
            StepFactory.inject_user("Start"),
            StepFactory.branch("alternate"),
        ]
        module = ModuleSpecFactory.with_branches(
            steps=steps,
            branch_name="alternate",
            branch_steps=[
                StepFactory.inject_user("Branch message"),
                StepFactory.await_agent(),
            ],
        )
        agent = stub_agent([AgentActionFactory.message("Branch response")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        branch_events = [e for e in result.events if e.type == "branch"]
        assert len(branch_events) == 1
        assert branch_events[0].payload["branch"] == "alternate"

        # Should have executed branch steps
        user_events = [e for e in result.events if e.type == "user"]
        assert any("Branch message" in e.payload.get("content", "") for e in user_events)

    def test_branch_to_nonexistent_branch(self, stub_agent: type[StubAgent]) -> None:
        """Test branching to a branch that doesn't exist."""
        steps = [
            StepFactory.inject_user("Start"),
            StepFactory.branch("nonexistent"),
            StepFactory.inject_user("After branch"),
            StepFactory.await_agent(),
        ]
        module = ModuleSpecFactory.create(steps=steps)
        agent = stub_agent([AgentActionFactory.message("Response")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Should continue to next step since branch doesn't exist
        user_events = [e for e in result.events if e.type == "user"]
        assert any("After branch" in e.payload.get("content", "") for e in user_events)


class TestRunnerEvaluation:
    """Tests for evaluation functionality."""

    def test_evaluation_contains_check(self, stub_agent: type[StubAgent]) -> None:
        """Test contains evaluation check."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[EvaluationCheckFactory.contains(value="help", expected=True)]
        )
        agent = stub_agent([AgentActionFactory.message("I can help you!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert "ContainsCheck" in result.evaluation.checks
        assert result.evaluation.checks["ContainsCheck"]["passed"] is True

    def test_evaluation_contains_not_found(self, stub_agent: type[StubAgent]) -> None:
        """Test contains check when string not found."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[EvaluationCheckFactory.contains(value="xyz123", expected=True)]
        )
        agent = stub_agent([AgentActionFactory.message("Hello there!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.checks["ContainsCheck"]["passed"] is False

    def test_evaluation_tool_called_check(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test tool_called evaluation check."""
        module = ModuleSpecFactory.with_shopify_tool()
        module.evaluation = [EvaluationCheckFactory.tool_called(tool="shopify", action="get_order")]

        agent = stub_agent(
            [
                AgentActionFactory.tool_call("shopify", "get_order", {"order_id": "ORD123"}),
                AgentActionFactory.message("Done."),
            ]
        )

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            result = runner.run()

        assert result.evaluation.checks["ToolCalledCheck"]["passed"] is True
        assert result.evaluation.checks["ToolCalledCheck"]["called"] is True

    def test_evaluation_tool_not_called(
        self, stub_agent: type[StubAgent], mock_shopify_tool: MagicMock
    ) -> None:
        """Test tool_called check when tool not called."""
        module = ModuleSpecFactory.with_shopify_tool()
        module.evaluation = [EvaluationCheckFactory.tool_called(tool="shopify", expected=True)]

        agent = stub_agent([AgentActionFactory.message("I can help without tools.")])

        with patch("sandboxy.core.runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = Runner(module=module, agent=agent)
            result = runner.run()

        assert result.evaluation.checks["ToolCalledCheck"]["passed"] is False
        assert result.evaluation.checks["ToolCalledCheck"]["called"] is False

    def test_evaluation_env_state_check(self, stub_agent: type[StubAgent]) -> None:
        """Test env_state evaluation check."""
        module = ModuleSpecFactory.create(initial_state={"status": "active"})
        module.evaluation = [EvaluationCheckFactory.env_state(key="status", value="active")]

        agent = stub_agent([AgentActionFactory.message("Done.")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.checks["EnvStateCheck"]["passed"] is True

    def test_evaluation_count_check(self, stub_agent: type[StubAgent]) -> None:
        """Test count evaluation check."""
        module = ModuleSpecFactory.create()
        module.evaluation = [EvaluationCheckFactory.count(target="agent_messages", min=1, max=3)]

        agent = stub_agent([AgentActionFactory.message("Response")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.checks["CountCheck"]["passed"] is True
        assert result.evaluation.checks["CountCheck"]["count"] == 1

    def test_evaluation_regex_check(self, stub_agent: type[StubAgent]) -> None:
        """Test regex evaluation check."""
        module = ModuleSpecFactory.create()
        module.evaluation = [EvaluationCheckFactory.regex(pattern=r"\d{3}-\d{4}")]

        agent = stub_agent([AgentActionFactory.message("Call 555-1234 for help")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.checks["RegexCheck"]["passed"] is True


class TestRunnerScoring:
    """Tests for scoring functionality."""

    def test_default_scoring(self, stub_agent: type[StubAgent]) -> None:
        """Test default scoring (weighted average)."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[
                EvaluationCheckFactory.contains(name="Check1", value="help"),
                EvaluationCheckFactory.contains(name="Check2", value="assist"),
            ]
        )
        agent = stub_agent([AgentActionFactory.message("I can help you!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Check1 passes, Check2 fails -> 0.5 average
        assert result.evaluation.score == pytest.approx(0.5)

    def test_weighted_scoring(self, stub_agent: type[StubAgent]) -> None:
        """Test scoring with weights."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[
                EvaluationCheckFactory.contains(name="Important", value="help"),
                EvaluationCheckFactory.contains(name="Minor", value="xyz"),
            ]
        )
        module.scoring = ScoringConfig(weights={"Important": 3.0, "Minor": 1.0})
        agent = stub_agent([AgentActionFactory.message("I can help!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Important (1.0 * 3.0) + Minor (0.0 * 1.0) / 4.0 = 0.75
        assert result.evaluation.score == pytest.approx(0.75)

    def test_formula_scoring(self, stub_agent: type[StubAgent]) -> None:
        """Test scoring with custom formula."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[
                EvaluationCheckFactory.contains(name="Check1", value="help"),
            ]
        )
        module.scoring = ScoringConfig(formula="Check1 * 100")
        agent = stub_agent([AgentActionFactory.message("I can help!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.score == pytest.approx(100.0)

    def test_normalized_scoring(self, stub_agent: type[StubAgent]) -> None:
        """Test score normalization."""
        module = ModuleSpecFactory.with_evaluation(
            checks=[EvaluationCheckFactory.contains(name="Check1", value="help")]
        )
        module.scoring = ScoringConfig(
            formula="Check1 * 50",
            normalize=True,
            min_score=0.0,
            max_score=100.0,
        )
        agent = stub_agent([AgentActionFactory.message("I can help!")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        # Score of 50 normalized to 0-1 range = 0.5
        assert result.evaluation.score == pytest.approx(0.5)


class TestRunResult:
    """Tests for RunResult class."""

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

    def test_to_json_with_indent(self) -> None:
        """Test JSON serialization with indentation."""
        result = RunResult(
            module_id="test/module",
            agent_id="test/agent",
            events=[],
        )
        json_str = result.to_json(indent=2)

        # Indented JSON should have newlines
        assert "\n" in json_str

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

    def test_pretty_format_with_tool_calls(self) -> None:
        """Test pretty format includes tool calls."""
        result = RunResult(
            module_id="test/module",
            agent_id="test/agent",
            events=[
                RunEvent(
                    type="tool_call",
                    payload={"tool": "shopify", "action": "get_order", "args": {"id": "123"}},
                ),
                RunEvent(
                    type="tool_result",
                    payload={"result": {"success": True, "data": "OK"}},
                ),
            ],
        )
        pretty = result.pretty()

        assert "TOOL CALL:" in pretty
        assert "shopify" in pretty
        assert "TOOL RESULT" in pretty


class TestRunnerWithYAMLModules:
    """Tests loading and running modules from YAML files."""

    def test_run_from_yaml_file(self, stub_agent: type[StubAgent], temp_yaml_file) -> None:
        """Test running a module loaded from YAML."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = """
id: test/yaml-module
description: Test module from YAML
environment:
  sandbox_type: local
  tools: []
  initial_state: {}
steps:
  - id: s1
    action: inject_user
    params:
      content: Hello from YAML
  - id: s2
    action: await_agent
    params: {}
evaluation: []
"""
        path = create_yaml(yaml_content)
        module = load_module(path)
        agent = stub_agent([AgentActionFactory.message("Response to YAML")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.module_id == "test/yaml-module"
        user_events = [e for e in result.events if e.type == "user"]
        assert user_events[0].payload["content"] == "Hello from YAML"

    def test_run_with_yaml_evaluation(self, stub_agent: type[StubAgent], temp_yaml_file) -> None:
        """Test evaluation checks defined in YAML."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = """
id: test/yaml-eval
description: Test module with evaluation
environment:
  sandbox_type: local
  tools: []
  initial_state:
    status: pending
steps:
  - id: s1
    action: inject_user
    params:
      content: Check the status
  - id: s2
    action: await_agent
    params: {}
evaluation:
  - name: StatusCheck
    kind: env_state
    key: status
    value: pending
"""
        path = create_yaml(yaml_content)
        module = load_module(path)
        agent = stub_agent([AgentActionFactory.message("Status is pending")])

        runner = Runner(module=module, agent=agent)
        result = runner.run()

        assert result.evaluation.checks["StatusCheck"]["passed"] is True
