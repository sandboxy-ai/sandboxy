"""Base agent interface and models."""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from sandboxy.core.state import Message

AgentKind = Literal["llm-prompt", "python-module", "http-endpoint"]


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    id: str
    name: str
    kind: AgentKind
    model: str = ""
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    impl: dict[str, Any] = Field(default_factory=dict)


class AgentAction(BaseModel):
    """Action returned by an agent after processing."""

    type: Literal["message", "tool_call", "stop"]
    content: str | None = None
    tool_name: str | None = None
    tool_action: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_call_id: str | None = None


class Agent(Protocol):
    """Protocol for agent implementations."""

    config: AgentConfig

    def step(
        self, history: list[Message], available_tools: list[dict[str, Any]] | None = None
    ) -> AgentAction:
        """Process conversation history and return next action.

        Args:
            history: Conversation history as list of messages.
            available_tools: Optional list of available tool schemas for function calling.

        Returns:
            Next action to take (message, tool call, or stop).
        """
        ...


class BaseAgent:
    """Base class for agent implementations."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def step(
        self, history: list[Message], available_tools: list[dict[str, Any]] | None = None
    ) -> AgentAction:
        """Process history and return action. Override in subclasses."""
        return AgentAction(type="stop")
