"""Base tool interface and models.

This module defines the core abstractions for tools:
    - ToolConfig: Configuration for instantiating a tool
    - ToolResult: Result of a tool invocation
    - Tool: Protocol defining the tool interface
    - BaseTool: Base implementation for custom tools
"""

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for a tool instance.

    Attributes:
        name: Unique identifier for this tool instance.
        type: Tool type identifier (e.g., 'yaml_tool', 'mock_lemonade').
        description: Human-readable description of the tool.
        config: Tool-specific configuration options.
    """

    name: str
    type: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool invocation.

    Attributes:
        success: Whether the invocation succeeded.
        data: Result data on success (type varies by action).
        error: Error message on failure.
    """

    success: bool
    data: Any = None
    error: str | None = None


class Tool(Protocol):
    """Protocol for tool implementations.

    Tools provide actions that agents can invoke to interact with
    simulated environments. Each tool has a name, description, and
    a set of available actions.

    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description of the tool's purpose.
    """

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
    """Base class for tool implementations.

    Subclass this to create custom tools. Override `invoke` to handle
    actions and `get_actions` to advertise available actions.

    Attributes:
        name: Tool instance name from config.
        description: Tool description from config.
        config: Tool-specific configuration dict.
    """

    def __init__(self, config: ToolConfig) -> None:
        """Initialize the tool from configuration.

        Args:
            config: Tool configuration containing name, description, and options.
        """
        self.name = config.name
        self.description = config.description
        self.config = config.config

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Invoke a tool action.

        Override in subclasses to implement action handling.

        Args:
            action: The action to perform.
            args: Arguments for the action.
            env_state: Current environment state (can be modified).

        Returns:
            Result of the action invocation.
        """
        return ToolResult(success=False, error=f"Unknown action: {action}")

    def get_actions(self) -> list[dict[str, Any]]:
        """Get list of available actions with their schemas.

        Override in subclasses to advertise available actions.

        Returns:
            List of action definitions with name, description, and parameters.
        """
        return []
