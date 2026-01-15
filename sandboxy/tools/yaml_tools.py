"""YAML-defined mock tools for declarative scenario creation.

This module enables defining tools entirely in YAML without writing Python code.
Tools can have static returns, parameterized returns, conditional logic, and
side effects that modify scenario state.

Example tool definition:
    tools:
      power_off_rack:
        description: "Power off a server rack"
        params:
          rack_id:
            type: string
            required: true
        returns: "Rack {rack_id} powered off."
        side_effects:
          - set: "rack_{rack_id}_status"
            value: "offline"
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from sandboxy.tools.base import ToolConfig, ToolResult

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Schema Models
# -----------------------------------------------------------------------------


class ParamSchema(BaseModel):
    """Schema for a tool parameter.

    Attributes:
        type: Parameter type (string, number, boolean, integer, array, object).
        description: Human-readable description of the parameter.
        required: Whether the parameter must be provided.
        default: Default value if not provided.
        enum: List of allowed values (for validation).
    """

    type: Literal["string", "number", "boolean", "integer", "array", "object"] = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None


class SideEffect(BaseModel):
    """A side effect that modifies scenario state when a tool is called.

    Attributes:
        set: State key to set (supports {param} substitution).
        value: Value to set (supports {param} and {state.key} substitution).
    """

    set: str
    value: Any

    def apply(self, state: dict[str, Any], params: dict[str, Any]) -> None:
        """Apply this side effect to the state.

        Args:
            state: Environment state dict to modify.
            params: Parameters from the tool invocation.
        """
        key = _interpolate(self.set, params, state)
        value = self.value

        # Interpolate string values
        if isinstance(value, str):
            value = _interpolate(value, params, state)

        state[key] = value


class ConditionalReturn(BaseModel):
    """A conditional return value based on state.

    Attributes:
        when: Condition expression to evaluate.
        value: Return value if condition is true.
    """

    when: str
    value: str


class ActionSpec(BaseModel):
    """Specification for a single tool action.

    Attributes:
        description: Human-readable description of the action.
        params: Parameter definitions for this action.
        returns: Return value (string or list of ConditionalReturn).
        returns_error: Error message to return when error_when is true.
        error_when: Condition expression that triggers an error.
        side_effects: State modifications to apply on success.
    """

    description: str = ""
    params: dict[str, ParamSchema] = Field(default_factory=dict)
    returns: str | list[ConditionalReturn] = ""
    returns_error: str | None = None
    error_when: str | None = None
    side_effects: list[SideEffect] = Field(default_factory=list)

    @field_validator("returns", mode="before")
    @classmethod
    def parse_returns(cls, v: Any) -> str | list[ConditionalReturn]:
        """Parse returns field - can be string or list of conditionals."""
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return [ConditionalReturn(**item) if isinstance(item, dict) else item for item in v]
        if isinstance(v, dict) and "conditions" in v:
            # Support { conditions: [...] } format
            return [
                ConditionalReturn(**item) if isinstance(item, dict) else item
                for item in v["conditions"]
            ]
        return str(v) if v else ""


class ToolSpec(BaseModel):
    """Specification for a complete YAML-defined tool.

    A tool can either have multiple actions (like existing mock tools) or
    be a simple single-action tool (just has returns directly).
    """

    name: str = ""
    description: str = ""

    # For multi-action tools
    actions: dict[str, ActionSpec] = Field(default_factory=dict)

    # For single-action tools (shorthand) - these become the default "call" action
    params: dict[str, ParamSchema] = Field(default_factory=dict)
    returns: str | list[ConditionalReturn] = ""
    returns_error: str | None = None
    error_when: str | None = None
    side_effects: list[SideEffect] = Field(default_factory=list)

    def get_effective_actions(self) -> dict[str, ActionSpec]:
        """Get all actions, including synthesized default action for simple tools."""
        if self.actions:
            return self.actions

        # Single-action tool - create a "call" action from top-level fields
        if self.returns or self.params or self.returns_error:
            return {
                "call": ActionSpec(
                    description=self.description,
                    params=self.params,
                    returns=self.returns,
                    returns_error=self.returns_error,
                    error_when=self.error_when,
                    side_effects=self.side_effects,
                )
            }

        return {}


class ToolLibrary(BaseModel):
    """A library of YAML-defined tools loaded from a file."""

    name: str = ""
    description: str = ""
    tools: dict[str, ToolSpec] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Expression Evaluation
# -----------------------------------------------------------------------------


def _interpolate(template: Any, params: dict[str, Any], state: dict[str, Any]) -> Any:
    """Interpolate {param} and {state.key} placeholders in a template string.

    Non-string values are returned unchanged.
    """
    if not isinstance(template, str):
        return template

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)

        # Check params first
        if key in params:
            return str(params[key])

        # Check state with state. prefix
        if key.startswith("state."):
            state_key = key[6:]
            return str(state.get(state_key, f"{{{key}}}"))

        # Check state directly
        if key in state:
            return str(state[key])

        # Not found - return original placeholder
        return match.group(0)

    return re.sub(r"\{(\w+(?:\.\w+)*)\}", replace, template)


def _evaluate_condition(expr: str, params: dict[str, Any], state: dict[str, Any]) -> bool:
    """Safely evaluate a condition expression.

    Supports:
        - Simple comparisons: "param == value", "state.key != 'foo'"
        - Boolean state checks: "state.is_active", "!state.is_disabled"
        - Parameterized keys: "state.rack_{rack_id}_powered == false"
    """
    if not expr or not expr.strip():
        return False

    # Interpolate any {param} references in the expression
    expr = _interpolate(expr, params, state)

    # Build evaluation context
    context: dict[str, Any] = {
        "true": True,
        "false": False,
        "True": True,
        "False": False,
        "none": None,
        "None": None,
    }
    context.update(params)
    context["state"] = state

    # Also expose state keys directly for convenience
    for key, value in state.items():
        if key.isidentifier():
            context[key] = value

    try:
        # Restrict evaluation to safe operations
        safe_builtins = {
            "True": True,
            "False": False,
            "None": None,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }
        return bool(eval(expr, {"__builtins__": safe_builtins}, context))  # noqa: S307
    except Exception as e:
        logger.debug("Condition evaluation failed for expression '%s': %s", expr, e)
        return False


# -----------------------------------------------------------------------------
# YAML Mock Tool Implementation
# -----------------------------------------------------------------------------


class YamlMockTool:
    """A tool implementation backed by YAML definitions.

    Implements the Tool protocol for seamless integration with the existing
    runner and agent systems.
    """

    def __init__(self, config: ToolConfig, spec: ToolSpec) -> None:
        """Initialize from config and spec.

        Args:
            config: Tool configuration (name, description, etc.)
            spec: YAML tool specification
        """
        self.name = config.name
        self.description = config.description or spec.description
        self.config = config.config
        self.spec = spec
        self._call_log: list[dict[str, Any]] = []

    @property
    def call_log(self) -> list[dict[str, Any]]:
        """Get log of all tool calls made."""
        return self._call_log

    def invoke(
        self,
        action: str,
        args: dict[str, Any],
        env_state: dict[str, Any],
    ) -> ToolResult:
        """Invoke a tool action.

        Args:
            action: The action to perform
            args: Arguments from the caller
            env_state: Current environment state (will be modified by side effects)

        Returns:
            ToolResult with success/error and data
        """
        actions = self.spec.get_effective_actions()

        if action not in actions:
            available = ", ".join(actions.keys()) or "none"
            return ToolResult(
                success=False,
                error=f"Unknown action '{action}'. Available: {available}",
            )

        action_spec = actions[action]

        # Validate and apply defaults to params
        validated_args = self._validate_params(action_spec, args)
        if isinstance(validated_args, ToolResult):
            return validated_args  # Validation error

        # Log the call
        self._call_log.append(
            {
                "action": action,
                "args": validated_args.copy(),
                "state_before": env_state.copy(),
            }
        )

        # Check for error condition
        if action_spec.error_when and _evaluate_condition(
            action_spec.error_when, validated_args, env_state
        ):
            error_msg = action_spec.returns_error or "Operation failed"
            error_msg = _interpolate(error_msg, validated_args, env_state)
            return ToolResult(success=False, error=error_msg)

        # Apply side effects
        for effect in action_spec.side_effects:
            effect.apply(env_state, validated_args)

        # Compute return value
        result_value = self._compute_return(action_spec, validated_args, env_state)

        return ToolResult(success=True, data=result_value)

    def _validate_params(
        self,
        action_spec: ActionSpec,
        args: dict[str, Any],
    ) -> dict[str, Any] | ToolResult:
        """Validate and normalize parameters.

        Returns validated args dict or ToolResult with error.
        """
        validated: dict[str, Any] = {}

        for name, schema in action_spec.params.items():
            if name in args:
                # TODO: Type coercion/validation
                validated[name] = args[name]
            elif schema.required:
                return ToolResult(
                    success=False,
                    error=f"Missing required parameter: {name}",
                )
            elif schema.default is not None:
                validated[name] = schema.default

        # Include any extra args not in schema (permissive mode)
        for name, value in args.items():
            if name not in validated:
                validated[name] = value

        return validated

    def _compute_return(
        self,
        action_spec: ActionSpec,
        params: dict[str, Any],
        state: dict[str, Any],
    ) -> Any:
        """Compute the return value for an action."""
        returns = action_spec.returns

        # Handle conditional returns
        if isinstance(returns, list):
            for cond in returns:
                if isinstance(cond, ConditionalReturn):
                    # Check "default" condition (always true)
                    if cond.when in ("default", "else", "otherwise", "true", "True"):
                        return _interpolate(cond.value, params, state)

                    if _evaluate_condition(cond.when, params, state):
                        return _interpolate(cond.value, params, state)

            # No condition matched - return empty
            return ""

        # Simple string return with interpolation
        return _interpolate(returns, params, state)

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available actions with their schemas for the agent."""
        result = []

        for name, action_spec in self.spec.get_effective_actions().items():
            # Build JSON Schema for parameters
            properties: dict[str, Any] = {}
            required: list[str] = []

            for param_name, param_schema in action_spec.params.items():
                prop: dict[str, Any] = {
                    "type": param_schema.type,
                }
                if param_schema.description:
                    prop["description"] = param_schema.description
                if param_schema.enum:
                    prop["enum"] = param_schema.enum
                if param_schema.default is not None:
                    prop["default"] = param_schema.default

                properties[param_name] = prop

                if param_schema.required:
                    required.append(param_name)

            result.append(
                {
                    "name": name,
                    "description": action_spec.description or self.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            )

        return result


# -----------------------------------------------------------------------------
# Tool Loading
# -----------------------------------------------------------------------------


class YamlToolLoader:
    """Loads YAML-defined tools from files and inline definitions."""

    # Default search paths for tool libraries
    DEFAULT_TOOL_DIRS = [
        Path("tools"),
        Path("sandboxy/tools/libraries"),
    ]

    def __init__(self, tool_dirs: list[Path] | None = None) -> None:
        """Initialize loader with search directories.

        Args:
            tool_dirs: Directories to search for tool library files.
                      Defaults to DEFAULT_TOOL_DIRS.
        """
        self.tool_dirs = tool_dirs or self.DEFAULT_TOOL_DIRS
        self._library_cache: dict[str, ToolLibrary] = {}

    def load_library(self, name: str) -> ToolLibrary:
        """Load a tool library by name.

        Searches for {name}.yml or {name}.yaml in tool directories.

        Args:
            name: Library name (without extension)

        Returns:
            Loaded ToolLibrary

        Raises:
            FileNotFoundError: If library file not found
        """
        if name in self._library_cache:
            return self._library_cache[name]

        # Search for the file
        for dir_path in self.tool_dirs:
            for ext in (".yml", ".yaml"):
                file_path = dir_path / f"{name}{ext}"
                if file_path.exists():
                    library = self._load_library_file(file_path)
                    self._library_cache[name] = library
                    return library

        msg = f"Tool library '{name}' not found in: {self.tool_dirs}"
        raise FileNotFoundError(msg)

    def load_library_file(self, path: Path) -> ToolLibrary:
        """Load a tool library from a specific file path.

        Args:
            path: Path to the YAML file

        Returns:
            Loaded ToolLibrary
        """
        return self._load_library_file(path)

    def _load_library_file(self, path: Path) -> ToolLibrary:
        """Internal: Load and parse a library file."""
        content = path.read_text()
        raw = yaml.safe_load(content)

        if not raw:
            return ToolLibrary(name=path.stem)

        # Parse tools
        tools: dict[str, ToolSpec] = {}
        raw_tools = raw.get("tools", {})

        for tool_name, tool_data in raw_tools.items():
            if isinstance(tool_data, dict):
                tool_data["name"] = tool_name
                tools[tool_name] = self._parse_tool_spec(tool_data)

        return ToolLibrary(
            name=raw.get("name", path.stem),
            description=raw.get("description", ""),
            tools=tools,
        )

    def _parse_tool_spec(self, data: dict[str, Any]) -> ToolSpec:
        """Parse a tool specification from raw YAML data."""
        # Parse params
        params: dict[str, ParamSchema] = {}
        raw_params = data.get("params", {})
        for name, param_data in raw_params.items():
            if isinstance(param_data, dict):
                params[name] = ParamSchema(**param_data)
            elif isinstance(param_data, str):
                # Shorthand: just the type
                params[name] = ParamSchema(type=param_data)  # type: ignore[arg-type]

        # Parse actions
        actions: dict[str, ActionSpec] = {}
        raw_actions = data.get("actions", {})
        for name, action_data in raw_actions.items():
            if isinstance(action_data, dict):
                actions[name] = self._parse_action_spec(action_data)

        # Parse side effects
        side_effects: list[SideEffect] = []
        raw_effects = data.get("side_effects", [])
        for effect_data in raw_effects:
            if isinstance(effect_data, dict):
                side_effects.append(SideEffect(**effect_data))

        return ToolSpec(
            name=data.get("name", ""),
            description=data.get("description", ""),
            actions=actions,
            params=params,
            returns=data.get("returns", ""),
            returns_error=data.get("returns_error"),
            error_when=data.get("error_when"),
            side_effects=side_effects,
        )

    def _parse_action_spec(self, data: dict[str, Any]) -> ActionSpec:
        """Parse an action specification from raw YAML data."""
        # Parse params
        params: dict[str, ParamSchema] = {}
        raw_params = data.get("params", {})
        for name, param_data in raw_params.items():
            if isinstance(param_data, dict):
                params[name] = ParamSchema(**param_data)
            elif isinstance(param_data, str):
                params[name] = ParamSchema(type=param_data)  # type: ignore[arg-type]

        # Parse side effects
        side_effects: list[SideEffect] = []
        raw_effects = data.get("side_effects", [])
        for effect_data in raw_effects:
            if isinstance(effect_data, dict):
                side_effects.append(SideEffect(**effect_data))

        return ActionSpec(
            description=data.get("description", ""),
            params=params,
            returns=data.get("returns", ""),
            returns_error=data.get("returns_error"),
            error_when=data.get("error_when"),
            side_effects=side_effects,
        )

    def parse_inline_tools(
        self,
        tools_data: dict[str, Any] | list[dict[str, Any]],
    ) -> dict[str, ToolSpec]:
        """Parse inline tool definitions from scenario YAML.

        Args:
            tools_data: Raw tools section from scenario YAML.
                       Can be a dict (name -> spec) or list of specs with names.

        Returns:
            Dictionary mapping tool name to ToolSpec
        """
        result: dict[str, ToolSpec] = {}

        if isinstance(tools_data, dict):
            for name, data in tools_data.items():
                if isinstance(data, dict):
                    data["name"] = name
                    result[name] = self._parse_tool_spec(data)
        elif isinstance(tools_data, list):
            for item in tools_data:
                if isinstance(item, dict) and "name" in item:
                    result[item["name"]] = self._parse_tool_spec(item)

        return result

    def create_tool_instances(
        self,
        specs: dict[str, ToolSpec],
    ) -> dict[str, YamlMockTool]:
        """Create tool instances from specifications.

        Args:
            specs: Dictionary of tool name to ToolSpec

        Returns:
            Dictionary of tool name to YamlMockTool instance
        """
        tools: dict[str, YamlMockTool] = {}

        for name, spec in specs.items():
            config = ToolConfig(
                name=name,
                type="yaml_mock",
                description=spec.description,
            )
            tools[name] = YamlMockTool(config, spec)

        return tools


# -----------------------------------------------------------------------------
# Integration Helper
# -----------------------------------------------------------------------------


def load_scenario_tools(
    scenario_data: dict[str, Any],
    tool_dirs: list[Path] | None = None,
    tool_overrides: dict[str, Any] | None = None,
) -> dict[str, YamlMockTool]:
    """Load all tools for a scenario from YAML data.

    Handles both `tools_from` library references and inline `tools` definitions.
    Inline tools override library tools with the same name.

    Args:
        scenario_data: Parsed scenario YAML
        tool_dirs: Optional tool search directories
        tool_overrides: Optional dict mapping "tool.action" to override response data.
                       Used by dataset benchmarking to inject test case data.

    Returns:
        Dictionary of tool name to YamlMockTool
    """
    loader = YamlToolLoader(tool_dirs)
    all_specs: dict[str, ToolSpec] = {}

    # Load from libraries first
    tools_from = scenario_data.get("tools_from", [])
    if isinstance(tools_from, str):
        tools_from = [tools_from]

    for lib_name in tools_from:
        # Strip extension if provided
        lib_name = Path(lib_name).stem
        try:
            library = loader.load_library(lib_name)
            all_specs.update(library.tools)
        except FileNotFoundError:
            logger.warning("Tool library '%s' not found, skipping", lib_name)

    # Load inline tools (override library tools)
    inline_tools = scenario_data.get("tools", {})
    if inline_tools:
        inline_specs = loader.parse_inline_tools(inline_tools)
        all_specs.update(inline_specs)

    tools = loader.create_tool_instances(all_specs)

    # Apply tool overrides if provided (for dataset benchmarking)
    if tool_overrides:
        for tool in tools.values():
            tool.set_overrides(tool_overrides)

    return tools
