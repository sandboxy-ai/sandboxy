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


class EvaluationCheck(BaseModel):
    """An evaluation check to run after module execution."""

    name: str
    kind: str  # "deterministic" | "llm"
    config: dict[str, Any] = Field(default_factory=dict)


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


class EvaluationResult(BaseModel):
    """Result of running evaluation checks."""

    checks: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    num_events: int = 0
    status: str = "ok"
