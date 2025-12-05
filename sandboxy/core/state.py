"""Core state models for Sandboxy MDL and runtime."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class SessionState(str, Enum):
    """State of an interactive session."""

    IDLE = "idle"  # Created but not started
    RUNNING = "running"  # Executing steps
    AWAITING_USER = "awaiting_user"  # Paused waiting for user input
    AWAITING_AGENT = "awaiting_agent"  # Waiting for LLM response
    PAUSED = "paused"  # Manually paused
    COMPLETED = "completed"  # All steps done
    ERROR = "error"  # Execution failed


class StepAction(str, Enum):
    """Valid step actions in MDL."""

    INJECT_USER = "inject_user"  # Add scripted user message
    AWAIT_USER = "await_user"  # Wait for real user input (interactive)
    AWAIT_AGENT = "await_agent"  # Wait for agent response
    BRANCH = "branch"  # Conditional branching
    TOOL_CALL = "tool_call"  # Direct tool invocation (not via agent)


class ToolCall(BaseModel):
    """A tool call made by the assistant."""

    id: str
    name: str
    arguments: str  # JSON string


class Message(BaseModel):
    """A message in the conversation history."""

    role: Role
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ToolRef(BaseModel):
    """Reference to a tool in a module's environment."""

    name: str
    type: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class EnvConfig(BaseModel):
    """Environment configuration for a module."""

    sandbox_type: str = "local"
    tools: list[ToolRef] = Field(default_factory=list)
    initial_state: dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    """A step in the module's execution flow.

    Actions:
        inject_user: Add a scripted user message
            params: {content: str}
        await_user: Wait for real user input (interactive sessions only)
            params: {prompt?: str, timeout?: int}
        await_agent: Wait for agent response
            params: {}
        branch: Conditional branching
            params: {branch_name: str}
        tool_call: Direct tool invocation
            params: {tool: str, action: str, args: dict}
    """

    id: str
    action: str  # See StepAction enum
    params: dict[str, Any] = Field(default_factory=dict)
    condition: str | None = None  # Optional condition expression for conditional steps


class BranchCondition(BaseModel):
    """Condition for branching in the execution flow."""

    expr: str
    next_step: str


class CheckKind(str, Enum):
    """Types of evaluation checks."""

    CONTAINS = "contains"  # Check if target contains/doesn't contain a value
    REGEX = "regex"  # Check if target matches a regex pattern
    COUNT = "count"  # Check count of items (min/max)
    TOOL_CALLED = "tool_called"  # Check if a tool was called
    EQUALS = "equals"  # Check if target equals a value
    ENV_STATE = "env_state"  # Check environment state value
    # Legacy support
    DETERMINISTIC = "deterministic"  # Raw Python expression (deprecated)
    LLM = "llm"  # LLM-based evaluation (not implemented)


class CheckTarget(str, Enum):
    """Valid targets for evaluation checks."""

    AGENT_MESSAGES = "agent_messages"  # All agent message content
    USER_MESSAGES = "user_messages"  # All user message content
    ALL_MESSAGES = "all_messages"  # All message content
    TOOL_CALLS = "tool_calls"  # List of tool calls
    LAST_AGENT_MESSAGE = "last_agent_message"  # Most recent agent message
    LAST_USER_MESSAGE = "last_user_message"  # Most recent user message


class EvaluationCheck(BaseModel):
    """An evaluation check to run after module execution.

    Predefined check types:
        contains: Check if target contains a string
            - target: what to search (e.g., "agent_messages")
            - value: string to look for
            - expected: True if should contain, False if should not (default: True)
            - case_sensitive: whether to do case-sensitive match (default: False)

        regex: Check if target matches a regex pattern
            - target: what to search
            - pattern: regex pattern
            - expected: True if should match, False if should not (default: True)

        count: Check count of items
            - target: what to count (e.g., "agent_messages", "tool_calls")
            - min: minimum count (optional)
            - max: maximum count (optional)

        tool_called: Check if a specific tool was called
            - tool: tool name
            - action: action name (optional)
            - expected: True if should be called, False if should not (default: True)

        equals: Check if a value equals expected
            - target: what to check (e.g., "env.order_status")
            - value: expected value

        env_state: Check environment state
            - key: state key to check
            - value: expected value

        deterministic: (deprecated) Raw Python expression
            - expr: Python expression string
    """

    name: str
    kind: str  # See CheckKind enum
    # Common fields
    target: str | None = None  # What to evaluate (see CheckTarget)
    value: Any = None  # Value to check against
    expected: bool = True  # Expected result (True = should match/contain)
    # Type-specific fields
    pattern: str | None = None  # For regex
    case_sensitive: bool = False  # For contains
    min: int | None = None  # For count
    max: int | None = None  # For count
    tool: str | None = None  # For tool_called
    action: str | None = None  # For tool_called
    key: str | None = None  # For env_state
    # Legacy support
    config: dict[str, Any] = Field(default_factory=dict)  # For deterministic/llm


class VariableOption(BaseModel):
    """An option for a select/dropdown variable."""

    value: str
    label: str


class ModuleVariable(BaseModel):
    """A configurable variable for a module."""

    name: str
    label: str
    description: str = ""
    type: str = "string"  # "string" | "number" | "boolean" | "select" | "slider"
    default: Any = None
    options: list[VariableOption] | None = None  # For select type
    min: float | None = None  # For slider type
    max: float | None = None  # For slider type
    step: float | None = None  # For slider type


class ScoringConfig(BaseModel):
    """Configuration for how the final score is computed."""

    # Score formula using check names as variables, e.g.:
    # "Profit * 2 + Reputation + CustomersServed * 5 - CustomersLost * 10"
    formula: str | None = None

    # If no formula, use weighted average. Default weight is 1.0.
    weights: dict[str, float] = Field(default_factory=dict)

    # Normalization settings
    normalize: bool = False  # Normalize score to 0-1 range
    min_score: float = 0.0  # Expected minimum for normalization
    max_score: float = 100.0  # Expected maximum for normalization


class ModuleSpec(BaseModel):
    """Complete specification for an MDL module."""

    id: str
    description: str = ""
    variables: list[ModuleVariable] = Field(default_factory=list)
    agent_config: dict[str, Any] = Field(default_factory=dict)  # Override agent settings
    environment: EnvConfig
    steps: list[Step] = Field(default_factory=list)
    branches: dict[str, list[Step]] = Field(default_factory=dict)
    evaluation: list[EvaluationCheck] = Field(default_factory=list)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)  # Score computation config


class EvaluationResult(BaseModel):
    """Result of running evaluation checks."""

    checks: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    num_events: int = 0
    status: str = "ok"
