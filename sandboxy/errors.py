"""Structured error types for Sandboxy.

Provides typed exceptions with error codes and details for better
error handling and debugging.
"""

from typing import Any


class SandboxyError(Exception):
    """Base exception for Sandboxy operations.

    All Sandboxy errors include:
    - A human-readable message
    - An error code for programmatic handling
    - Optional details dictionary for debugging
    """

    code: str = "SANDBOXY_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code or self.__class__.code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": self.code,
            "message": str(self),
            "details": self.details,
        }


class ConfigurationError(SandboxyError):
    """Error in configuration or environment setup."""

    code = "CONFIG_ERROR"


class ModuleError(SandboxyError):
    """Error related to module operations."""

    code = "MODULE_ERROR"


class ModuleParseError(ModuleError):
    """Error parsing a module definition (MDL/YAML)."""

    code = "MODULE_PARSE_ERROR"

    def __init__(self, message: str, *, path: str | None = None, line: int | None = None):
        details = {}
        if path:
            details["path"] = path
        if line:
            details["line"] = line
        super().__init__(message, details=details)


class ModuleNotFoundError(ModuleError):
    """Module not found."""

    code = "MODULE_NOT_FOUND"

    def __init__(self, module_id: str):
        super().__init__(f"Module not found: {module_id}", details={"module_id": module_id})


class ToolError(SandboxyError):
    """Error related to tool operations."""

    code = "TOOL_ERROR"


class ToolLoadError(ToolError):
    """Error loading a tool."""

    code = "TOOL_LOAD_ERROR"

    def __init__(self, message: str, *, tool_name: str):
        super().__init__(message, details={"tool": tool_name})


class ToolExecutionError(ToolError):
    """Error executing a tool action."""

    code = "TOOL_EXECUTION_ERROR"

    def __init__(self, message: str, *, tool_name: str, action: str | None = None):
        details = {"tool": tool_name}
        if action:
            details["action"] = action
        super().__init__(message, details=details)


class EvaluationError(SandboxyError):
    """Error during expression evaluation."""

    code = "EVAL_ERROR"

    def __init__(self, message: str, *, expression: str | None = None):
        details = {}
        if expression:
            details["expression"] = expression
        super().__init__(message, details=details)


class AgentError(SandboxyError):
    """Error related to agent operations."""

    code = "AGENT_ERROR"


class AgentNotFoundError(AgentError):
    """Agent not found."""

    code = "AGENT_NOT_FOUND"

    def __init__(self, agent_id: str):
        super().__init__(f"Agent not found: {agent_id}", details={"agent_id": agent_id})


class ProviderError(SandboxyError):
    """Error from an LLM provider."""

    code = "PROVIDER_ERROR"

    def __init__(self, message: str, *, provider: str, model: str | None = None):
        details = {"provider": provider}
        if model:
            details["model"] = model
        super().__init__(message, details=details)


class ValidationError(SandboxyError):
    """Input validation error."""

    code = "VALIDATION_ERROR"

    def __init__(self, message: str, *, field: str | None = None):
        details = {}
        if field:
            details["field"] = field
        super().__init__(message, details=details)


class SessionError(SandboxyError):
    """Error related to session operations."""

    code = "SESSION_ERROR"


class SessionNotFoundError(SessionError):
    """Session not found."""

    code = "SESSION_NOT_FOUND"

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}", details={"session_id": session_id})
