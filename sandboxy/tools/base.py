"""Base tool interface and models."""

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for a tool instance."""

    name: str
    type: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool invocation."""

    success: bool
    data: Any = None
    error: str | None = None


class Tool(Protocol):
    """Protocol for tool implementations."""

    name: str
    description: str

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Invoke a tool action.

        Args:
            action: The action to perform (e.g., "get_order", "refund_order").
            args: Arguments for the action.
            env_state: Current environment state (can be modified by tools).

        Returns:
            Result of the tool invocation.
        """
        ...

    def get_actions(self) -> list[dict[str, Any]]:
        """Get list of available actions with their schemas.

        Returns:
            List of action definitions with name, description, and parameters.
        """
        ...


class BaseTool:
    """Base class for tool implementations."""

    def __init__(self, config: ToolConfig) -> None:
        self.name = config.name
        self.description = config.description
        self.config = config.config

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Invoke a tool action. Override in subclasses."""
        return ToolResult(success=False, error=f"Unknown action: {action}")

    def get_actions(self) -> list[dict[str, Any]]:
        """Get list of available actions. Override in subclasses."""
        return []
