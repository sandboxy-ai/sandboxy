"""Tests for core state models."""

from sandboxy.core.state import (
    EnvConfig,
    EvaluationCheck,
    EvaluationResult,
    Message,
    ModuleSpec,
    ModuleVariable,
    ScoringConfig,
    SessionState,
    Step,
    StepAction,
    ToolCall,
    ToolRef,
    VariableOption,
)


class TestSessionState:
    """Tests for SessionState enum."""

    def test_all_states_defined(self) -> None:
        """Test that all expected states are defined."""
        expected = [
            "IDLE",
            "RUNNING",
            "AWAITING_USER",
            "AWAITING_AGENT",
            "PAUSED",
            "COMPLETED",
            "ERROR",
        ]
        for state in expected:
            assert hasattr(SessionState, state)

    def test_state_values(self) -> None:
        """Test state enum values."""
        assert SessionState.IDLE.value == "idle"
        assert SessionState.RUNNING.value == "running"
        assert SessionState.COMPLETED.value == "completed"
        assert SessionState.ERROR.value == "error"


class TestStepAction:
    """Tests for StepAction enum."""

    def test_all_actions_defined(self) -> None:
        """Test that all expected actions are defined."""
        expected = ["INJECT_USER", "AWAIT_USER", "AWAIT_AGENT", "BRANCH", "TOOL_CALL"]
        for action in expected:
            assert hasattr(StepAction, action)

    def test_action_values(self) -> None:
        """Test action enum values."""
        assert StepAction.INJECT_USER.value == "inject_user"
        assert StepAction.AWAIT_AGENT.value == "await_agent"


class TestMessage:
    """Tests for Message model."""

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_name is None
        assert msg.tool_calls is None

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_create_tool_message(self) -> None:
        """Test creating a tool result message."""
        msg = Message(
            role="tool",
            content='{"status": "ok"}',
            tool_name="shopify",
            tool_call_id="call_123",
        )
        assert msg.role == "tool"
        assert msg.tool_name == "shopify"
        assert msg.tool_call_id == "call_123"

    def test_message_with_tool_calls(self) -> None:
        """Test assistant message with tool calls."""
        tool_call = ToolCall(
            id="call_abc",
            name="shopify__get_order",
            arguments='{"order_id": "123"}',
        )
        msg = Message(
            role="assistant",
            content="",
            tool_calls=[tool_call],
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_abc"

    def test_message_serialization(self) -> None:
        """Test message serializes to dict."""
        msg = Message(role="user", content="Test")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Test"


class TestToolCall:
    """Tests for ToolCall model."""

    def test_create_tool_call(self) -> None:
        """Test creating a tool call."""
        tc = ToolCall(
            id="call_123",
            name="shopify__refund_order",
            arguments='{"order_id": "ORD456"}',
        )
        assert tc.id == "call_123"
        assert tc.name == "shopify__refund_order"
        assert tc.arguments == '{"order_id": "ORD456"}'


class TestToolRef:
    """Tests for ToolRef model."""

    def test_create_tool_ref(self) -> None:
        """Test creating a tool reference."""
        ref = ToolRef(
            name="shopify",
            type="mock_shopify",
            description="Mock store",
            config={"api_key": "test"},
        )
        assert ref.name == "shopify"
        assert ref.type == "mock_shopify"
        assert ref.config["api_key"] == "test"

    def test_tool_ref_defaults(self) -> None:
        """Test tool reference default values."""
        ref = ToolRef(name="test", type="mock")
        assert ref.description == ""
        assert ref.config == {}


class TestEnvConfig:
    """Tests for EnvConfig model."""

    def test_create_env_config(self) -> None:
        """Test creating environment config."""
        env = EnvConfig(
            sandbox_type="local",
            tools=[ToolRef(name="t1", type="mock")],
            initial_state={"key": "value"},
        )
        assert env.sandbox_type == "local"
        assert len(env.tools) == 1
        assert env.initial_state["key"] == "value"

    def test_env_config_defaults(self) -> None:
        """Test environment config defaults."""
        env = EnvConfig()
        assert env.sandbox_type == "local"
        assert env.tools == []
        assert env.initial_state == {}


class TestStep:
    """Tests for Step model."""

    def test_create_step(self) -> None:
        """Test creating a step."""
        step = Step(
            id="s1",
            action="inject_user",
            params={"content": "Hello"},
        )
        assert step.id == "s1"
        assert step.action == "inject_user"
        assert step.params["content"] == "Hello"
        assert step.condition is None

    def test_step_with_condition(self) -> None:
        """Test step with conditional."""
        step = Step(
            id="s1",
            action="inject_user",
            params={},
            condition="x > 5",
        )
        assert step.condition == "x > 5"

    def test_step_defaults(self) -> None:
        """Test step default values."""
        step = Step(id="s1", action="await_agent")
        assert step.params == {}
        assert step.condition is None


class TestEvaluationCheck:
    """Tests for EvaluationCheck model."""

    def test_create_contains_check(self) -> None:
        """Test creating a contains check."""
        check = EvaluationCheck(
            name="CheckHelp",
            kind="contains",
            target="agent_messages",
            value="help",
            expected=True,
            case_sensitive=False,
        )
        assert check.name == "CheckHelp"
        assert check.kind == "contains"
        assert check.value == "help"
        assert check.case_sensitive is False

    def test_create_tool_called_check(self) -> None:
        """Test creating a tool_called check."""
        check = EvaluationCheck(
            name="CheckTool",
            kind="tool_called",
            tool="shopify",
            action="get_order",
            expected=True,
        )
        assert check.kind == "tool_called"
        assert check.tool == "shopify"
        assert check.action == "get_order"

    def test_create_env_state_check(self) -> None:
        """Test creating an env_state check."""
        check = EvaluationCheck(
            name="CheckState",
            kind="env_state",
            key="balance",
            value=100,
        )
        assert check.kind == "env_state"
        assert check.key == "balance"
        assert check.value == 100

    def test_check_defaults(self) -> None:
        """Test evaluation check defaults."""
        check = EvaluationCheck(name="Test", kind="contains")
        assert check.expected is True
        assert check.case_sensitive is False
        assert check.config == {}


class TestModuleVariable:
    """Tests for ModuleVariable model."""

    def test_create_string_variable(self) -> None:
        """Test creating a string variable."""
        var = ModuleVariable(
            name="customer_name",
            label="Customer Name",
            type="string",
            default="John",
        )
        assert var.name == "customer_name"
        assert var.type == "string"
        assert var.default == "John"

    def test_create_select_variable(self) -> None:
        """Test creating a select variable."""
        var = ModuleVariable(
            name="difficulty",
            label="Difficulty",
            type="select",
            options=[
                VariableOption(value="easy", label="Easy"),
                VariableOption(value="hard", label="Hard"),
            ],
        )
        assert var.type == "select"
        assert len(var.options) == 2
        assert var.options[0].value == "easy"

    def test_create_slider_variable(self) -> None:
        """Test creating a slider variable."""
        var = ModuleVariable(
            name="budget",
            label="Budget",
            type="slider",
            min=0,
            max=1000,
            step=10,
            default=100,
        )
        assert var.type == "slider"
        assert var.min == 0
        assert var.max == 1000
        assert var.step == 10


class TestScoringConfig:
    """Tests for ScoringConfig model."""

    def test_create_scoring_config(self) -> None:
        """Test creating scoring configuration."""
        config = ScoringConfig(
            formula="check1 * 2 + check2",
            weights={"check1": 2.0},
            normalize=True,
            min_score=0.0,
            max_score=100.0,
        )
        assert config.formula == "check1 * 2 + check2"
        assert config.weights["check1"] == 2.0
        assert config.normalize is True

    def test_scoring_config_defaults(self) -> None:
        """Test scoring config defaults."""
        config = ScoringConfig()
        assert config.formula is None
        assert config.weights == {}
        assert config.normalize is False
        assert config.min_score == 0.0
        assert config.max_score == 100.0


class TestModuleSpec:
    """Tests for ModuleSpec model."""

    def test_create_minimal_module(self) -> None:
        """Test creating a minimal module."""
        module = ModuleSpec(
            id="test/minimal",
            environment=EnvConfig(),
        )
        assert module.id == "test/minimal"
        assert module.description == ""
        assert len(module.steps) == 0

    def test_create_full_module(self) -> None:
        """Test creating a full module."""
        module = ModuleSpec(
            id="test/full",
            description="Full module",
            variables=[ModuleVariable(name="x", label="X")],
            agent_config={"temperature": 0.7},
            environment=EnvConfig(
                tools=[ToolRef(name="t", type="mock")],
                initial_state={"key": "value"},
            ),
            steps=[Step(id="s1", action="await_agent")],
            branches={"alt": [Step(id="b1", action="inject_user", params={})]},
            evaluation=[EvaluationCheck(name="c1", kind="contains")],
            scoring=ScoringConfig(formula="c1"),
        )
        assert module.id == "test/full"
        assert len(module.variables) == 1
        assert len(module.environment.tools) == 1
        assert len(module.steps) == 1
        assert "alt" in module.branches
        assert len(module.evaluation) == 1


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_create_result(self) -> None:
        """Test creating evaluation result."""
        result = EvaluationResult(
            checks={"check1": {"passed": True}},
            score=0.85,
            num_events=10,
            status="ok",
        )
        assert result.score == 0.85
        assert result.num_events == 10
        assert result.status == "ok"
        assert result.checks["check1"]["passed"] is True

    def test_result_defaults(self) -> None:
        """Test evaluation result defaults."""
        result = EvaluationResult()
        assert result.checks == {}
        assert result.score == 0.0
        assert result.num_events == 0
        assert result.status == "ok"
