"""Tests for AsyncRunner module."""

from unittest.mock import MagicMock, patch

import pytest

from sandboxy.agents.base import AgentAction
from sandboxy.core.async_runner import AsyncRunner, RunEvent
from sandboxy.core.state import (
    EnvConfig,
    EvaluationCheck,
    Message,
    ModuleSpec,
    ScoringConfig,
    SessionState,
    Step,
    StepAction,
)
from sandboxy.tools.base import ToolResult

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create a mock agent."""
    agent = MagicMock()
    agent.step.return_value = AgentAction(
        type="message",
        content="Hello from the agent!",
    )
    return agent


@pytest.fixture
def simple_module() -> ModuleSpec:
    """Create a simple module with inject_user and await_agent steps."""
    return ModuleSpec(
        id="test/simple",
        name="Simple Test",
        version="1.0.0",
        steps=[
            Step(
                id="step1",
                action=StepAction.INJECT_USER.value,
                params={"content": "Hello agent!"},
            ),
            Step(
                id="step2",
                action=StepAction.AWAIT_AGENT.value,
                params={},
            ),
        ],
        environment=EnvConfig(tools=[], initial_state={"counter": 0}),
        evaluation=[],
        scoring=ScoringConfig(),
    )


@pytest.fixture
def module_with_tools() -> ModuleSpec:
    """Create a module with tool configuration.

    Note: This module references tools but tests should mock ToolLoader.from_env_config
    to avoid needing actual tool implementations.
    """
    return ModuleSpec(
        id="test/with-tools",
        name="Test With Tools",
        version="1.0.0",
        steps=[
            Step(
                id="step1", action=StepAction.INJECT_USER.value, params={"content": "Get my order"}
            ),
            Step(id="step2", action=StepAction.AWAIT_AGENT.value, params={}),
        ],
        environment=EnvConfig(
            # Use empty tools list for fixtures - tests that need tools will mock
            tools=[],
            initial_state={"cash_balance": 1000.0},
        ),
        evaluation=[],
        scoring=ScoringConfig(),
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
    tool.invoke.return_value = ToolResult(
        success=True, data={"order_id": "ORD123", "status": "completed", "total": 99.99}
    )
    return tool


@pytest.fixture
def module_with_branch() -> ModuleSpec:
    """Create a module with branching."""
    return ModuleSpec(
        id="test/branch",
        name="Test Branch",
        version="1.0.0",
        steps=[
            Step(id="step1", action=StepAction.BRANCH.value, params={"branch_name": "alt_path"}),
        ],
        branches={
            "alt_path": [
                Step(
                    id="alt1", action=StepAction.INJECT_USER.value, params={"content": "Alt path"}
                ),
            ],
        },
        environment=EnvConfig(tools=[], initial_state={}),
        evaluation=[],
        scoring=ScoringConfig(),
    )


@pytest.fixture
def module_with_evaluation() -> ModuleSpec:
    """Create a module with evaluation checks."""
    return ModuleSpec(
        id="test/eval",
        name="Test Eval",
        version="1.0.0",
        steps=[
            Step(id="step1", action=StepAction.INJECT_USER.value, params={"content": "Hello"}),
            Step(id="step2", action=StepAction.AWAIT_AGENT.value, params={}),
        ],
        environment=EnvConfig(tools=[], initial_state={"score": 100}),
        evaluation=[
            EvaluationCheck(
                name="greeting_check",
                kind="contains",
                target="agent_messages",
                value="Hello",
                expected=True,
            ),
            EvaluationCheck(
                name="env_score",
                kind="env_state",
                key="score",
                value=100,
            ),
        ],
        scoring=ScoringConfig(weights={"greeting_check": 1.0, "env_score": 1.0}),
    )


# -----------------------------------------------------------------------------
# Helper Tests
# -----------------------------------------------------------------------------


class TestRunEvent:
    """Tests for RunEvent model."""

    def test_create_user_event(self) -> None:
        """Test creating a user event."""
        event = RunEvent(
            type="user",
            payload={"content": "Hello", "scripted": True},
        )
        assert event.type == "user"
        assert event.payload["content"] == "Hello"

    def test_default_payload_is_empty_dict(self) -> None:
        """Test that default payload is empty dict."""
        event = RunEvent(type="completed")
        assert event.payload == {}


# -----------------------------------------------------------------------------
# AsyncRunner Initialization Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerInit:
    """Tests for AsyncRunner initialization."""

    def test_initializes_with_module_and_agent(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that AsyncRunner initializes correctly."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner.module == simple_module
        assert runner.agent == mock_agent
        assert runner.state == SessionState.IDLE
        assert runner.history == []
        assert runner.events == []

    def test_copies_initial_state(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test that initial state is copied, not referenced."""
        runner = AsyncRunner(simple_module, mock_agent)

        # Modify runner's env_state
        runner.env_state["counter"] = 999

        # Original should be unchanged
        assert simple_module.environment.initial_state["counter"] == 0

    def test_session_state_property(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test session_state property."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner.session_state == SessionState.IDLE


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerRun:
    """Tests for AsyncRunner.run method."""

    @pytest.mark.asyncio
    async def test_run_simple_module(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test running a simple module."""
        runner = AsyncRunner(simple_module, mock_agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        # Should have: user event, agent event, completed event
        event_types = [e.type for e in events]
        assert "user" in event_types
        assert "agent" in event_types
        assert "completed" in event_types

    @pytest.mark.asyncio
    async def test_run_updates_state_to_running(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that run updates state to RUNNING."""
        runner = AsyncRunner(simple_module, mock_agent)

        async for event in runner.run():
            if event.type == "user":
                # During execution, state should be RUNNING
                assert runner.state in [SessionState.RUNNING, SessionState.AWAITING_AGENT]
            if event.type == "completed":
                assert runner.state == SessionState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_handles_exception(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that run handles exceptions gracefully."""
        mock_agent.step.side_effect = Exception("Agent error")
        runner = AsyncRunner(simple_module, mock_agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        # Should end with error event
        assert events[-1].type == "error"
        assert runner.state == SessionState.ERROR


# -----------------------------------------------------------------------------
# Step Handler Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerInjectUser:
    """Tests for inject_user step handling."""

    @pytest.mark.asyncio
    async def test_inject_user_adds_to_history(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that inject_user adds message to history."""
        runner = AsyncRunner(simple_module, mock_agent)

        async for _ in runner.run():
            pass

        # First message in history should be the injected user message
        assert len(runner.history) >= 1
        assert runner.history[0].role == "user"
        assert runner.history[0].content == "Hello agent!"

    @pytest.mark.asyncio
    async def test_inject_user_yields_event(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that inject_user yields a user event."""
        runner = AsyncRunner(simple_module, mock_agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        user_events = [e for e in events if e.type == "user"]
        assert len(user_events) >= 1
        assert user_events[0].payload["scripted"] is True


class TestAsyncRunnerAwaitAgent:
    """Tests for await_agent step handling."""

    @pytest.mark.asyncio
    async def test_await_agent_calls_agent_step(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that await_agent calls agent.step()."""
        runner = AsyncRunner(simple_module, mock_agent)

        async for _ in runner.run():
            pass

        mock_agent.step.assert_called()

    @pytest.mark.asyncio
    async def test_await_agent_adds_response_to_history(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that agent response is added to history."""
        runner = AsyncRunner(simple_module, mock_agent)

        async for _ in runner.run():
            pass

        assistant_msgs = [m for m in runner.history if m.role == "assistant"]
        assert len(assistant_msgs) >= 1
        assert assistant_msgs[0].content == "Hello from the agent!"

    @pytest.mark.asyncio
    async def test_await_agent_handles_tool_call(
        self, module_with_tools: ModuleSpec, mock_shopify_tool: MagicMock
    ) -> None:
        """Test that await_agent handles tool calls."""
        agent = MagicMock()
        # First return tool call, then message
        agent.step.side_effect = [
            AgentAction(
                type="tool_call",
                tool_name="shopify",
                tool_action="get_order",
                tool_args={"order_id": "ORD123"},
                tool_call_id="call_123",
            ),
            AgentAction(type="message", content="Here's your order info"),
        ]

        with patch("sandboxy.core.async_runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = AsyncRunner(module_with_tools, agent)
            events: list[RunEvent] = []

            async for event in runner.run():
                events.append(event)

        event_types = [e.type for e in events]
        assert "tool_call" in event_types
        assert "tool_result" in event_types

    @pytest.mark.asyncio
    async def test_await_agent_handles_stop_action(self, simple_module: ModuleSpec) -> None:
        """Test that await_agent handles stop action."""
        agent = MagicMock()
        agent.step.return_value = AgentAction(type="stop")

        runner = AsyncRunner(simple_module, agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        # Should complete without agent message
        assert events[-1].type == "completed"


class TestAsyncRunnerBranch:
    """Tests for branch step handling."""

    @pytest.mark.asyncio
    async def test_branch_switches_to_new_steps(
        self, module_with_branch: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that branch switches to alternate steps."""
        runner = AsyncRunner(module_with_branch, mock_agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        # Should have branch event
        branch_events = [e for e in events if e.type == "branch"]
        assert len(branch_events) == 1
        assert branch_events[0].payload["branch"] == "alt_path"

        # Should execute alt path
        user_events = [e for e in events if e.type == "user"]
        assert any(e.payload.get("content") == "Alt path" for e in user_events)

    @pytest.mark.asyncio
    async def test_branch_to_nonexistent_continues(self, mock_agent: MagicMock) -> None:
        """Test that branching to nonexistent branch continues."""
        module = ModuleSpec(
            id="test/bad-branch",
            name="Bad Branch",
            version="1.0.0",
            steps=[
                Step(
                    id="step1",
                    action=StepAction.BRANCH.value,
                    params={"branch_name": "nonexistent"},
                ),
                Step(
                    id="step2",
                    action=StepAction.INJECT_USER.value,
                    params={"content": "After branch"},
                ),
            ],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[],
            scoring=ScoringConfig(),
        )

        runner = AsyncRunner(module, mock_agent)
        events: list[RunEvent] = []

        async for event in runner.run():
            events.append(event)

        # Should still complete
        assert events[-1].type == "completed"


class TestAsyncRunnerDirectToolCall:
    """Tests for direct tool_call step handling."""

    @pytest.mark.asyncio
    async def test_direct_tool_call_invokes_tool(self, mock_shopify_tool: MagicMock) -> None:
        """Test that direct tool_call invokes the tool."""
        module = ModuleSpec(
            id="test/direct-tool",
            name="Direct Tool",
            version="1.0.0",
            steps=[
                Step(
                    id="step1",
                    action=StepAction.TOOL_CALL.value,
                    params={
                        "tool": "shopify",
                        "action": "get_order",
                        "args": {"order_id": "ORD123"},
                    },
                ),
            ],
            environment=EnvConfig(
                tools=[],  # Will be mocked
                initial_state={},
            ),
            evaluation=[],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()

        with patch("sandboxy.core.async_runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = AsyncRunner(module, agent)
            events: list[RunEvent] = []

            async for event in runner.run():
                events.append(event)

        # Should have tool_call and tool_result events
        tool_call_events = [e for e in events if e.type == "tool_call"]
        tool_result_events = [e for e in events if e.type == "tool_result"]

        assert len(tool_call_events) == 1
        assert tool_call_events[0].payload["direct"] is True
        assert len(tool_result_events) == 1


# -----------------------------------------------------------------------------
# User Input Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerUserInput:
    """Tests for provide_input method."""

    def test_provide_input_when_not_awaiting_raises(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that provide_input raises when not awaiting."""
        runner = AsyncRunner(simple_module, mock_agent)

        with pytest.raises(RuntimeError, match="Not currently awaiting"):
            runner.provide_input("Hello")


# -----------------------------------------------------------------------------
# Event Injection Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerInjectEvent:
    """Tests for inject_event method."""

    def test_inject_event_calls_tool(
        self, module_with_tools: ModuleSpec, mock_shopify_tool: MagicMock
    ) -> None:
        """Test that inject_event calls the tool's trigger_event action."""
        agent = MagicMock()

        # Set up the mock tool to handle trigger_event
        mock_shopify_tool.invoke.return_value = ToolResult(
            success=True, data={"event": "new_order", "triggered": True}
        )

        with patch("sandboxy.core.async_runner.ToolLoader.from_env_config") as mock_loader:
            mock_loader.return_value = {"shopify": mock_shopify_tool}

            runner = AsyncRunner(module_with_tools, agent)
            result = runner.inject_event("shopify", "new_order", {"order_id": "ORD999"})

            # Verify the tool was called with trigger_event action
            mock_shopify_tool.invoke.assert_called_once()
            call_args = mock_shopify_tool.invoke.call_args
            assert call_args[0][0] == "trigger_event"
            assert "event" in call_args[0][1]
            assert result["triggered"] is True

    def test_inject_event_raises_for_unknown_tool(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that inject_event raises for unknown tool."""
        runner = AsyncRunner(simple_module, mock_agent)

        with pytest.raises(ValueError, match="Tool not found"):
            runner.inject_event("nonexistent", "event", {})


# -----------------------------------------------------------------------------
# Evaluation Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerEvaluation:
    """Tests for evaluation checks."""

    @pytest.mark.asyncio
    async def test_contains_check_passes(
        self, module_with_evaluation: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that contains check passes when value found."""
        mock_agent.step.return_value = AgentAction(
            type="message",
            content="Hello there!",  # Contains "Hello"
        )

        runner = AsyncRunner(module_with_evaluation, mock_agent)

        async for event in runner.run():
            if event.type == "completed":
                evaluation = event.payload["evaluation"]
                assert evaluation["checks"]["greeting_check"]["passed"] is True

    @pytest.mark.asyncio
    async def test_contains_check_fails(
        self, module_with_evaluation: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test that contains check fails when value not found."""
        mock_agent.step.return_value = AgentAction(
            type="message",
            content="Goodbye!",  # Does not contain "Hello"
        )

        runner = AsyncRunner(module_with_evaluation, mock_agent)

        async for event in runner.run():
            if event.type == "completed":
                evaluation = event.payload["evaluation"]
                assert evaluation["checks"]["greeting_check"]["passed"] is False

    @pytest.mark.asyncio
    async def test_env_state_check(
        self, module_with_evaluation: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test env_state evaluation check."""
        runner = AsyncRunner(module_with_evaluation, mock_agent)

        async for event in runner.run():
            if event.type == "completed":
                evaluation = event.payload["evaluation"]
                assert evaluation["checks"]["env_score"]["passed"] is True


class TestAsyncRunnerCheckTypes:
    """Tests for different check types."""

    def test_check_contains_case_insensitive(self) -> None:
        """Test contains check with case insensitivity."""
        module = ModuleSpec(
            id="test/contains",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[
                EvaluationCheck(
                    name="test",
                    kind="contains",
                    target="agent_messages",
                    value="HELLO",
                    expected=True,
                    case_sensitive=False,
                ),
            ],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()
        runner = AsyncRunner(module, agent)
        runner.history = [Message(role="assistant", content="hello world")]

        result = runner._check_contains(module.evaluation[0])

        assert result["passed"] is True
        assert result["found"] is True

    def test_check_regex(self) -> None:
        """Test regex evaluation check."""
        module = ModuleSpec(
            id="test/regex",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[
                EvaluationCheck(
                    name="test",
                    kind="regex",
                    target="agent_messages",
                    pattern=r"\d{3}-\d{4}",  # Phone pattern
                    expected=True,
                ),
            ],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()
        runner = AsyncRunner(module, agent)
        runner.history = [Message(role="assistant", content="Call me at 555-1234")]

        result = runner._check_regex(module.evaluation[0])

        assert result["passed"] is True
        assert result["matched"] is True

    def test_check_count(self) -> None:
        """Test count evaluation check."""
        module = ModuleSpec(
            id="test/count",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[
                EvaluationCheck(
                    name="test",
                    kind="count",
                    target="agent_messages",
                    min=2,
                    max=5,
                ),
            ],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()
        runner = AsyncRunner(module, agent)
        runner.history = [
            Message(role="assistant", content="First"),
            Message(role="assistant", content="Second"),
            Message(role="assistant", content="Third"),
        ]

        result = runner._check_count(module.evaluation[0])

        assert result["passed"] is True
        assert result["count"] == 3

    def test_check_tool_called(self) -> None:
        """Test tool_called evaluation check."""
        module = ModuleSpec(
            id="test/tool",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[
                EvaluationCheck(
                    name="test",
                    kind="tool_called",
                    tool="shopify",
                    action="get_order",
                    expected=True,
                ),
            ],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()
        runner = AsyncRunner(module, agent)
        runner.events = [
            RunEvent(type="tool_call", payload={"tool": "shopify", "action": "get_order"}),
        ]

        result = runner._check_tool_called(module.evaluation[0])

        assert result["passed"] is True
        assert result["called"] is True

    def test_check_equals(self) -> None:
        """Test equals evaluation check."""
        module = ModuleSpec(
            id="test/equals",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[
                EvaluationCheck(
                    name="test",
                    kind="equals",
                    target="env.balance",
                    value=500,
                ),
            ],
            scoring=ScoringConfig(),
        )

        agent = MagicMock()
        runner = AsyncRunner(module, agent)
        runner.env_state = {"balance": 500}

        result = runner._check_equals(module.evaluation[0])

        assert result["passed"] is True


# -----------------------------------------------------------------------------
# Scoring Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerScoring:
    """Tests for scoring calculations."""

    def test_weighted_average(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test weighted average calculation."""
        runner = AsyncRunner(simple_module, mock_agent)

        values = {"check1": 1.0, "check2": 0.5}
        weights = {"check1": 2.0, "check2": 1.0}

        result = runner._weighted_average(values, weights)

        # (1.0 * 2.0 + 0.5 * 1.0) / (2.0 + 1.0) = 2.5 / 3.0 ≈ 0.833
        assert abs(result - 0.833) < 0.01

    def test_weighted_average_default_weight(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test weighted average with default weight of 1.0."""
        runner = AsyncRunner(simple_module, mock_agent)

        values = {"check1": 1.0, "check2": 0.0}
        weights = {}  # No explicit weights, defaults to 1.0

        result = runner._weighted_average(values, weights)

        assert result == 0.5  # (1.0 + 0.0) / 2

    def test_weighted_average_empty(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test weighted average with empty values."""
        runner = AsyncRunner(simple_module, mock_agent)

        result = runner._weighted_average({}, {})

        assert result == 0.0

    def test_compute_score_with_formula(self, mock_agent: MagicMock) -> None:
        """Test score computation with formula."""
        module = ModuleSpec(
            id="test/formula",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[],
            scoring=ScoringConfig(formula="check1 * 2 + check2"),
        )

        runner = AsyncRunner(module, mock_agent)
        checks = {"check1": 10.0, "check2": 5.0}

        score = runner._compute_score(checks)

        assert score == 25.0  # 10 * 2 + 5

    def test_compute_score_normalized(self, mock_agent: MagicMock) -> None:
        """Test score normalization."""
        module = ModuleSpec(
            id="test/normalize",
            name="Test",
            version="1.0.0",
            steps=[],
            environment=EnvConfig(tools=[], initial_state={}),
            evaluation=[],
            scoring=ScoringConfig(
                normalize=True,
                min_score=0.0,
                max_score=100.0,
            ),
        )

        runner = AsyncRunner(module, mock_agent)
        checks = {"check1": 50.0}  # Will be weighted to 50.0

        score = runner._compute_score(checks)

        # Normalized: (50 - 0) / (100 - 0) = 0.5
        assert score == 0.5


# -----------------------------------------------------------------------------
# Target Helpers Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerTargetHelpers:
    """Tests for _get_target_text and _get_target_list helpers."""

    def test_get_target_text_agent_messages(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test getting agent messages text."""
        runner = AsyncRunner(simple_module, mock_agent)
        runner.history = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello"),
            Message(role="assistant", content="How are you?"),
        ]

        text = runner._get_target_text("agent_messages")

        assert "Hello" in text
        assert "How are you?" in text
        assert "Hi" not in text  # User message excluded

    def test_get_target_text_last_agent_message(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test getting last agent message."""
        runner = AsyncRunner(simple_module, mock_agent)
        runner.history = [
            Message(role="assistant", content="First"),
            Message(role="assistant", content="Last"),
        ]

        text = runner._get_target_text("last_agent_message")

        assert text == "Last"

    def test_get_target_list_tool_calls(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test getting tool calls list."""
        runner = AsyncRunner(simple_module, mock_agent)
        runner.events = [
            RunEvent(type="user", payload={}),
            RunEvent(type="tool_call", payload={"tool": "shopify"}),
            RunEvent(type="tool_result", payload={}),
        ]

        items = runner._get_target_list("tool_calls")

        assert len(items) == 1
        assert items[0].type == "tool_call"


# -----------------------------------------------------------------------------
# Pass Condition Tests
# -----------------------------------------------------------------------------


class TestAsyncRunnerPassCondition:
    """Tests for _evaluate_pass_condition helper."""

    def test_evaluate_greater_than(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test > condition."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(10.0, ">5") is True
        assert runner._evaluate_pass_condition(3.0, ">5") is False

    def test_evaluate_less_than(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test < condition."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(3.0, "<5") is True
        assert runner._evaluate_pass_condition(10.0, "<5") is False

    def test_evaluate_greater_or_equal(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test >= condition."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(5.0, ">=5") is True
        assert runner._evaluate_pass_condition(6.0, ">=5") is True
        assert runner._evaluate_pass_condition(4.0, ">=5") is False

    def test_evaluate_equals(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test == condition."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(5.0, "==5") is True
        assert runner._evaluate_pass_condition(6.0, "==5") is False

    def test_evaluate_not_equals(self, simple_module: ModuleSpec, mock_agent: MagicMock) -> None:
        """Test != condition."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(6.0, "!=5") is True
        assert runner._evaluate_pass_condition(5.0, "!=5") is False

    def test_evaluate_invalid_returns_true(
        self, simple_module: ModuleSpec, mock_agent: MagicMock
    ) -> None:
        """Test invalid condition returns True (passes)."""
        runner = AsyncRunner(simple_module, mock_agent)

        assert runner._evaluate_pass_condition(5.0, "invalid") is True
