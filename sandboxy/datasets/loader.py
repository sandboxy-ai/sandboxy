"""Dataset loader for multi-case benchmarking."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TestCase:
    """Single test case from a dataset."""

    id: str
    expected: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    tool_responses: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dataset:
    """Collection of test cases."""

    id: str
    name: str = ""
    description: str = ""
    scenario_id: str | None = None
    cases: list[TestCase] = field(default_factory=list)
    source_path: Path | None = None


def load_dataset(path: Path) -> Dataset:
    """Load dataset from YAML file.

    Supports both manual case definitions and generators.

    Args:
        path: Path to the dataset YAML file

    Returns:
        Dataset with loaded/generated test cases

    """
    with open(path) as f:
        data = yaml.safe_load(f)

    dataset_id = data.get("id", path.stem)
    dataset = Dataset(
        id=dataset_id,
        name=data.get("name", dataset_id),
        description=data.get("description", ""),
        scenario_id=data.get("scenario_id"),
        source_path=path,
    )

    if "cases" in data:
        for case_data in data["cases"]:
            expected_raw = case_data.get("expected")
            if expected_raw is None:
                expected = []
            elif isinstance(expected_raw, list):
                expected = expected_raw
            else:
                expected = [expected_raw]

            case = TestCase(
                id=case_data.get("id", f"case_{len(dataset.cases)}"),
                expected=expected,
                variables=case_data.get("variables", {}),
                tool_responses=case_data.get("tool_responses", {}),
                tags=case_data.get("tags", []),
                metadata=case_data.get("metadata", {}),
            )
            dataset.cases.append(case)

    if "generator" in data:
        generated = _generate_cases(data["generator"])
        dataset.cases.extend(generated)

    return dataset


def load_multiple_datasets(paths: list[Path]) -> Dataset:
    """Load and merge multiple datasets."""
    if not paths:
        return Dataset(id="empty", name="Empty Dataset")

    merged = load_dataset(paths[0])

    for path in paths[1:]:
        ds = load_dataset(path)
        merged.cases.extend(ds.cases)
        merged.id = f"{merged.id}+{ds.id}"
        merged.name = f"{merged.name} + {ds.name}"

    return merged


def _generate_cases(config: dict[str, Any]) -> list[TestCase]:
    """Generate cases from dimension combinations."""
    dimensions = config.get("dimensions", {})
    rules = config.get("rules", [])
    tool_mapping = config.get("tool_mapping", {})

    if not dimensions:
        return []

    dim_names = list(dimensions.keys())
    dim_values = [dimensions[name] for name in dim_names]

    cases = []
    for i, combo in enumerate(product(*dim_values)):
        case_data = dict(zip(dim_names, combo, strict=True))
        expected = _find_expected(case_data, rules)
        tool_responses = _build_tool_responses(case_data, tool_mapping)

        cases.append(
            TestCase(
                id=f"gen_{i:04d}",
                expected=expected,
                variables=case_data.copy(),
                tool_responses=tool_responses,
            )
        )

    return cases


def _find_expected(case_data: dict[str, Any], rules: list[dict]) -> list[str]:
    """Find expected outcome(s) from rules."""
    for rule in rules:
        if "when" in rule:
            if _matches_rule(case_data, rule["when"]):
                expected = rule.get("expected")
                if expected is None:
                    return []
                return expected if isinstance(expected, list) else [expected]
        elif "otherwise" in rule or "expected" in rule:
            expected = rule.get("expected")
            if expected is None:
                return []
            return expected if isinstance(expected, list) else [expected]

    return []


def _matches_rule(data: dict[str, Any], conditions: dict[str, Any]) -> bool:
    """Check if case data matches rule conditions."""
    for key, condition in conditions.items():
        value = data.get(key)

        if isinstance(condition, dict):
            if "gte" in condition and value < condition["gte"]:
                return False
            if "lte" in condition and value > condition["lte"]:
                return False
            if "gt" in condition and value <= condition["gt"]:
                return False
            if "lt" in condition and value >= condition["lt"]:
                return False
            if "eq" in condition and value != condition["eq"]:
                return False
            if "ne" in condition and value == condition["ne"]:
                return False
            if "in" in condition and value not in condition["in"]:
                return False
        elif value != condition:
            return False

    return True


def _build_tool_responses(
    case_data: dict[str, Any], tool_mapping: dict[str, Any]
) -> dict[str, Any]:
    """Build tool response overrides from case data and mapping."""
    tool_responses: dict[str, Any] = {}

    for tool_name, mapping in tool_mapping.items():
        response: dict[str, Any] = {}
        for response_key, source_key in mapping.items():
            if isinstance(source_key, str) and source_key in case_data:
                response[response_key] = case_data[source_key]
            else:
                response[response_key] = source_key
        tool_responses[tool_name] = response

    return tool_responses
