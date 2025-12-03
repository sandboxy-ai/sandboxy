"""Core state models for Sandboxy MDL and runtime."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


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
    """A step in the module's execution flow."""

    id: str
    action: str  # "inject_user", "await_agent", "branch"
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
