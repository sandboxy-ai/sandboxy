"""MDL (Module Definition Language) parser - YAML to ModuleSpec."""

import re
from pathlib import Path
from typing import Any

import yaml

from sandboxy.core.state import (
    EnvConfig,
    EvaluationCheck,
    ModuleSpec,
    ModuleVariable,
    Step,
    ToolRef,
    VariableOption,
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

    # Parse variables
    variables = []
    for v in raw.get("variables", []):
        options = None
        if v.get("options"):
            options = [
                VariableOption(value=o["value"], label=o["label"])
                for o in v["options"]
            ]
        variables.append(
            ModuleVariable(
                name=v["name"],
                label=v.get("label", v["name"]),
                description=v.get("description", ""),
                type=v.get("type", "string"),
                default=v.get("default"),
                options=options,
                min=v.get("min"),
                max=v.get("max"),
                step=v.get("step"),
            )
        )

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

    # Parse steps (with condition support)
    steps = [
        Step(
            id=s["id"],
            action=s["action"],
            params=s.get("params", {}),
            condition=s.get("condition"),
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
                condition=s.get("condition"),
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

    # Parse agent_config
    agent_config = raw.get("agent_config", {})

    return ModuleSpec(
        id=raw["id"],
        description=raw.get("description", ""),
        variables=variables,
        agent_config=agent_config,
        environment=environment,
        steps=steps,
        branches=branches,
        evaluation=evaluation,
    )


def interpolate_template(text: str, variables: dict[str, Any]) -> str:
    """Interpolate variables into a template string.

    Supports:
    - {{variable}} - Simple variable substitution
    - {{#if condition}}...{{else if condition}}...{{else}}...{{/if}} - Conditional blocks with else-if

    Args:
        text: Template string with {{variable}} placeholders.
        variables: Dictionary of variable values.

    Returns:
        Interpolated string.
    """
    if not text:
        return text

    # Process conditional blocks with support for else-if chains
    # Match {{#if ...}}...{{/if}} blocks
    if_pattern = re.compile(
        r'\{\{#if\s+(.+?)\}\}(.*?)\{\{/if\}\}',
        re.DOTALL
    )

    def eval_if_block(match: re.Match) -> str:
        condition = match.group(1).strip()
        body = match.group(2) or ""

        # Parse the body for else-if and else clauses
        # Split by {{else if ...}} and {{else}}
        parts = re.split(r'\{\{else if\s+(.+?)\}\}|\{\{else\}\}', body)

        # parts[0] is the content for the first if condition
        # Then alternating: condition (or None for else), content

        # Build list of (condition, content) tuples
        branches: list[tuple[str | None, str]] = [(condition, parts[0])]

        i = 1
        while i < len(parts):
            if i + 1 < len(parts) and parts[i] is not None:
                # This is an else-if: parts[i] is condition, parts[i+1] is content
                branches.append((parts[i].strip(), parts[i + 1]))
                i += 2
            elif parts[i] is None:
                # This is an else: content is in the next part
                if i + 1 < len(parts):
                    branches.append((None, parts[i + 1]))
                    i += 2
                else:
                    i += 1
            else:
                # Orphaned content (shouldn't happen in well-formed templates)
                branches.append((None, parts[i]))
                i += 1

        # Evaluate branches in order
        for cond, content in branches:
            if cond is None:
                # This is the else clause - always matches
                return content.strip()
            try:
                if _eval_condition(cond, variables):
                    return content.strip()
            except Exception:
                continue

        # No branch matched
        return ""

    text = if_pattern.sub(eval_if_block, text)

    # Simple variable substitution: {{variable}}
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1).strip()
        return str(variables.get(var_name, "{{var_name}}"))

    var_pattern = re.compile(r'\{\{(\w+)\}\}')
    text = var_pattern.sub(replace_var, text)

    return text


def _eval_condition(condition: str, variables: dict[str, Any]) -> bool:
    """Safely evaluate a condition expression.

    Args:
        condition: Condition expression (e.g., "sophistication >= 7").
        variables: Dictionary of variable values.

    Returns:
        Boolean result of condition evaluation.
    """
    # Safe builtins for condition evaluation
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

    # Create evaluation context
    safe_globals = {"__builtins__": safe_builtins}
    safe_globals.update(variables)

    try:
        return bool(eval(condition, safe_globals, {}))
    except Exception:
        return False


def apply_variables(module: ModuleSpec, variables: dict[str, Any]) -> ModuleSpec:
    """Apply variable values to a module, interpolating templates.

    Args:
        module: Module specification.
        variables: Dictionary of variable values (from user or defaults).

    Returns:
        New ModuleSpec with interpolated values.
    """
    # Build complete variable dict with defaults
    var_dict: dict[str, Any] = {}
    for var in module.variables:
        var_dict[var.name] = var.default
    var_dict.update(variables)

    # Interpolate agent_config system_prompt
    agent_config = dict(module.agent_config)
    if "system_prompt" in agent_config:
        agent_config["system_prompt"] = interpolate_template(
            agent_config["system_prompt"], var_dict
        )

    # Interpolate step params and filter by condition
    new_steps: list[Step] = []
    for step in module.steps:
        # Check condition if present
        if step.condition:
            if not _eval_condition(step.condition, var_dict):
                continue  # Skip this step

        # Interpolate params
        new_params = {}
        for key, value in step.params.items():
            if isinstance(value, str):
                new_params[key] = interpolate_template(value, var_dict)
            else:
                new_params[key] = value

        new_steps.append(
            Step(
                id=step.id,
                action=step.action,
                params=new_params,
                condition=None,  # Condition already evaluated
            )
        )

    # Return new module with interpolated values
    return ModuleSpec(
        id=module.id,
        description=module.description,
        variables=module.variables,
        agent_config=agent_config,
        environment=module.environment,
        steps=new_steps,
        branches=module.branches,  # TODO: interpolate branches too if needed
        evaluation=module.evaluation,
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
    valid_actions = {"inject_user", "await_user", "await_agent", "branch", "tool_call"}
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
