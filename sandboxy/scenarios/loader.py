"""Scenario loader - load scenario definitions from YAML files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GoalSpec(BaseModel):
    """Specification for a scenario goal."""

    id: str
    name: str
    description: str = ""
    points: int = 0
    detection: dict[str, Any] = Field(default_factory=dict)


class StepSpec(BaseModel):
    """Specification for a scenario step."""

    id: str
    action: str  # inject_user, await_user, await_agent
    params: dict[str, Any] = Field(default_factory=dict)


class McpServerSpec(BaseModel):
    """Specification for an MCP server connection.

    Supports two modes:
    - Local (stdio): Set `command` and optionally `args`/`env`
    - Remote (HTTP): Set `url` and optionally `headers`
    """

    name: str

    # Local server (stdio transport)
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    # Remote server (HTTP transport - SSE or Streamable HTTP)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    transport: str = "auto"  # "auto", "sse", or "streamable_http"


class ScenarioSpec(BaseModel):
    """Complete specification for a scenario."""

    id: str
    name: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)

    # Tool configuration
    tools_from: list[str] = Field(default_factory=list)
    tools: dict[str, Any] = Field(default_factory=dict)

    # MCP server connections (real tools)
    mcp_servers: list[McpServerSpec] = Field(default_factory=list)

    # State and prompts
    initial_state: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str = ""

    # Conversation flow
    steps: list[StepSpec] = Field(default_factory=list)

    # Evaluation
    goals: list[GoalSpec] = Field(default_factory=list)
    evaluation: list[dict[str, Any]] = Field(default_factory=list)
    scoring: dict[str, Any] = Field(default_factory=dict)


def load_scenario(path: Path) -> ScenarioSpec:
    """Load a scenario from a YAML file.

    Args:
        path: Path to the scenario YAML file

    Returns:
        Parsed ScenarioSpec

    Raises:
        ValueError: If the file cannot be loaded or parsed
    """
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e
    except FileNotFoundError as e:
        raise ValueError(f"File not found: {path}") from e

    if not isinstance(raw, dict):
        raise ValueError("Scenario must be a YAML mapping")

    return parse_scenario(raw)


def parse_scenario(raw: dict[str, Any]) -> ScenarioSpec:
    """Parse a raw dictionary into a ScenarioSpec.

    Args:
        raw: Raw dictionary from YAML parsing

    Returns:
        Parsed ScenarioSpec
    """
    # Parse tools_from (can be string or list)
    tools_from = raw.get("tools_from", [])
    if isinstance(tools_from, str):
        tools_from = [tools_from]

    # Parse MCP servers
    mcp_servers: list[McpServerSpec] = []
    for server in raw.get("mcp_servers", []):
        if isinstance(server, dict):
            mcp_servers.append(
                McpServerSpec(
                    name=server.get("name", "unnamed"),
                    # Local (stdio) transport
                    command=server.get("command"),
                    args=server.get("args", []),
                    env=server.get("env", {}),
                    # Remote (HTTP) transport
                    url=server.get("url"),
                    headers=server.get("headers", {}),
                    transport=server.get("transport", "auto"),
                )
            )

    # Parse steps
    steps: list[StepSpec] = []
    for s in raw.get("steps", []):
        steps.append(
            StepSpec(
                id=s.get("id", f"step_{len(steps)}"),
                action=s.get("action", "await_agent"),
                params=s.get("params", {}),
            )
        )

    # Parse goals
    goals: list[GoalSpec] = []
    for g in raw.get("goals", []):
        goals.append(
            GoalSpec(
                id=g.get("id", f"goal_{len(goals)}"),
                name=g.get("name", ""),
                description=g.get("description", ""),
                points=g.get("points", 0),
                detection=g.get("detection", {}),
            )
        )

    return ScenarioSpec(
        id=raw.get("id", "unnamed"),
        name=raw.get("name", raw.get("id", "Unnamed Scenario")),
        description=raw.get("description", ""),
        category=raw.get("category", ""),
        tags=raw.get("tags", []),
        tools_from=tools_from,
        tools=raw.get("tools", {}),
        mcp_servers=mcp_servers,
        initial_state=raw.get("initial_state", {}),
        system_prompt=raw.get("system_prompt", ""),
        steps=steps,
        goals=goals,
        evaluation=raw.get("evaluation", []),
        scoring=raw.get("scoring", {}),
    )


# -----------------------------------------------------------------------------
# Variable Interpolation
# -----------------------------------------------------------------------------


def _interpolate_string(text: str, variables: dict[str, Any]) -> str:
    """Interpolate {variable} placeholders in a string."""
    if not isinstance(text, str):
        return text

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        # Keep original placeholder if not found
        return match.group(0)

    return re.sub(r"\{(\w+)\}", replace, text)


def _interpolate_value(value: Any, variables: dict[str, Any]) -> Any:
    """Recursively interpolate variables in a value."""
    if isinstance(value, str):
        return _interpolate_string(value, variables)
    if isinstance(value, dict):
        return {k: _interpolate_value(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_value(item, variables) for item in value]
    return value


def apply_scenario_variables(spec: ScenarioSpec, variables: dict[str, Any]) -> ScenarioSpec:
    """Apply variable substitutions to a scenario.

    Interpolates {variable} placeholders in:
    - system_prompt
    - step params (especially content)
    - initial_state values

    Args:
        spec: Original scenario specification
        variables: Dictionary of variable name to value

    Returns:
        New ScenarioSpec with interpolated values
    """
    # Interpolate system prompt
    new_system_prompt = _interpolate_string(spec.system_prompt, variables)

    # Interpolate initial state
    new_initial_state = _interpolate_value(spec.initial_state, variables)

    # Interpolate steps
    new_steps: list[StepSpec] = []
    for step in spec.steps:
        new_params = _interpolate_value(dict(step.params), variables)
        new_steps.append(
            StepSpec(
                id=step.id,
                action=step.action,
                params=new_params,
            )
        )

    # Interpolate description
    new_description = _interpolate_string(spec.description, variables)

    return ScenarioSpec(
        id=spec.id,
        name=spec.name,
        description=new_description,
        category=spec.category,
        tags=spec.tags,
        tools_from=spec.tools_from,
        tools=spec.tools,  # Tools are not interpolated - they have their own param system
        mcp_servers=spec.mcp_servers,
        initial_state=new_initial_state,
        system_prompt=new_system_prompt,
        steps=new_steps,
        goals=spec.goals,
        evaluation=spec.evaluation,
        scoring=spec.scoring,
    )
