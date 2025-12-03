"""MDL (Module Definition Language) parser - YAML to ModuleSpec."""

from pathlib import Path
from typing import Any

import yaml

from sandboxy.core.state import (
    EnvConfig,
    EvaluationCheck,
    ModuleSpec,
    Step,
    ToolRef,
)


class MDLParseError(Exception):
    """Error parsing MDL module."""

    pass


def load_module(path: Path) -> ModuleSpec:
    """Load and parse an MDL module from a YAML file.

    Args:
        path: Path to the YAML module file.

    Returns:
        Parsed ModuleSpec.

    Raises:
        MDLParseError: If the file cannot be parsed or is invalid.
    """
    try:
        raw: dict[str, Any] = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise MDLParseError(f"Invalid YAML: {e}") from e
    except FileNotFoundError as e:
        raise MDLParseError(f"File not found: {path}") from e

    if not isinstance(raw, dict):
        raise MDLParseError("Module must be a YAML mapping")

    return parse_module(raw)


def parse_module(raw: dict[str, Any]) -> ModuleSpec:
    """Parse a raw dictionary into a ModuleSpec.

    Args:
        raw: Raw dictionary from YAML parsing.

    Returns:
        Parsed ModuleSpec.

    Raises:
        MDLParseError: If required fields are missing or invalid.
    """
    if "id" not in raw:
        raise MDLParseError("Module must have an 'id' field")

    # Parse environment
    env_raw = raw.get("environment", {})
    tools = [
        ToolRef(
            name=t["name"],
            type=t["type"],
            description=t.get("description", ""),
            config=t.get("config", {}),
        )
        for t in env_raw.get("tools", [])
    ]
    environment = EnvConfig(
        sandbox_type=env_raw.get("sandbox_type", "local"),
        tools=tools,
        initial_state=env_raw.get("initial_state", {}),
    )

    # Parse steps
    steps = [
        Step(
            id=s["id"],
            action=s["action"],
            params=s.get("params", {}),
        )
        for s in raw.get("steps", [])
    ]

    # Parse branches
    branches: dict[str, list[Step]] = {}
    for name, branch_steps in (raw.get("branches") or {}).items():
        branches[name] = [
            Step(
                id=s["id"],
                action=s["action"],
                params=s.get("params", {}),
            )
            for s in branch_steps
        ]

    # Parse evaluation
    evaluation = [
        EvaluationCheck(
            name=e["name"],
            kind=e["kind"],
            config=e.get("config", {}),
        )
        for e in raw.get("evaluation", [])
    ]

    return ModuleSpec(
        id=raw["id"],
        description=raw.get("description", ""),
        environment=environment,
        steps=steps,
        branches=branches,
        evaluation=evaluation,
    )


def validate_module(path: Path) -> list[str]:
    """Validate an MDL module and return any errors.

    Args:
        path: Path to the YAML module file.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    try:
        module = load_module(path)
    except MDLParseError as e:
        return [str(e)]

    # Validate steps have valid actions
    valid_actions = {"inject_user", "await_agent", "branch"}
    for step in module.steps:
        if step.action not in valid_actions:
            errors.append(f"Step '{step.id}' has invalid action: {step.action}")

    # Validate branch references exist
    for step in module.steps:
        if step.action == "branch":
            branch_name = step.params.get("branch_name")
            if branch_name and branch_name not in module.branches:
                errors.append(f"Step '{step.id}' references unknown branch: {branch_name}")

    # Validate evaluation checks have valid kinds
    valid_kinds = {"deterministic", "llm"}
    for check in module.evaluation:
        if check.kind not in valid_kinds:
            errors.append(f"Evaluation '{check.name}' has invalid kind: {check.kind}")

    return errors
