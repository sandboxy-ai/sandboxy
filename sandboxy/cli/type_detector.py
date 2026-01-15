"""YAML type detection for unified CLI dispatcher."""

from typing import Any, Literal

YamlType = Literal["scenario", "module"]

VALID_TYPES: set[str] = {"scenario", "module"}


def detect_yaml_type(data: dict[str, Any]) -> YamlType:
    """Detect YAML type from structure.

    Detection priority:
    1. Explicit `type:` field
    2. Scenario: has `goals` or `tools_from`
    3. Module (legacy): has `environment.sandbox_type`

    Args:
        data: Parsed YAML data

    Returns:
        Detected type string

    Raises:
        ValueError: If type cannot be detected

    """
    # Explicit type field takes priority
    if "type" in data:
        explicit_type = data["type"]
        if explicit_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid type '{explicit_type}'. Valid types: {', '.join(sorted(VALID_TYPES))}"
            )
        return explicit_type  # type: ignore[return-value]

    # Scenario: has goals or tools_from
    if "goals" in data or "tools_from" in data:
        return "scenario"

    # Module (legacy): has environment with sandbox_type
    if "environment" in data:
        env = data.get("environment", {})
        if isinstance(env, dict) and "sandbox_type" in env:
            return "module"

    # Default to scenario - the unified format handles everything
    return "scenario"
