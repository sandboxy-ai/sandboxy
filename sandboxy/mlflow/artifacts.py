"""Artifact generation for MLflow integration.

Generates human-readable summaries and prepares artifact directories
for upload to MLflow.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandboxy.scenarios.unified import RunResult


def generate_summary(
    result: RunResult | dict | object,
    scenario_name: str,
    model: str,
) -> str:
    """Generate human-readable summary text.

    Handles both RunResult (unified) and ScenarioResult (legacy) formats.

    Args:
        result: Run result from scenario execution (any format)
        scenario_name: Human-readable scenario name
        model: Model identifier

    Returns:
        Formatted summary text
    """
    # Extract fields from various result formats
    if isinstance(result, dict):
        error = result.get("error")
        evaluation = result.get("evaluation")
        latency_ms = result.get("latency_ms")
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        score = result.get("score", 0)
        goals_achieved = result.get("goals_achieved", [])
    else:
        error = getattr(result, "error", None)
        evaluation = getattr(result, "evaluation", None)
        latency_ms = getattr(result, "latency_ms", None)
        input_tokens = getattr(result, "input_tokens", 0) or 0
        output_tokens = getattr(result, "output_tokens", 0) or 0
        score = getattr(result, "score", 0)
        goals_achieved = getattr(result, "goals_achieved", [])

    # Determine status
    status = "FAILED" if error else "PASSED"
    timestamp = datetime.now(UTC).isoformat()

    lines = [
        "Sandboxy Run Summary",
        "=" * 20,
        f"Scenario: {scenario_name}",
        f"Model: {model}",
        f"Status: {status}",
        f"Timestamp: {timestamp}",
        "",
    ]

    # Scores section - handle both unified and legacy formats
    if evaluation:
        if isinstance(evaluation, dict):
            goals = evaluation.get("goals", [])
            total = evaluation.get("total_score", 0)
            max_score = evaluation.get("max_score", 0)
            pct = evaluation.get("percentage", 0)
        else:
            goals = getattr(evaluation, "goals", []) or []
            total = getattr(evaluation, "total_score", 0)
            max_score = getattr(evaluation, "max_score", 0)
            pct = getattr(evaluation, "percentage", 0)

        if goals:
            lines.append("Scores:")
            for goal in goals:
                if isinstance(goal, dict):
                    name = goal.get("name", "unknown")
                    goal_score = goal.get("score", 0)
                    passed = goal.get("passed", False)
                else:
                    name = getattr(goal, "name", "unknown")
                    goal_score = getattr(goal, "score", 0)
                    passed = getattr(goal, "passed", False)
                check = "✓" if passed else "✗"
                lines.append(f"  {name}: {goal_score:.1f} {check}")

            lines.append(f"  score_total: {total:.1f}/{max_score:.1f} ({pct:.1f}%)")
            lines.append("")
    elif score or goals_achieved:
        # Legacy ScenarioResult format
        lines.append("Scores:")
        lines.append(f"  Total Score: {score}")
        if goals_achieved:
            lines.append(f"  Goals Achieved: {', '.join(goals_achieved)}")
        lines.append("")

    # Timing section
    if latency_ms:
        lines.append("Timing:")
        lines.append(f"  Total: {latency_ms}ms")
        lines.append("")

    # Tokens section
    if input_tokens or output_tokens:
        total_tokens = input_tokens + output_tokens
        lines.append("Tokens:")
        lines.append(f"  Input: {input_tokens}")
        lines.append(f"  Output: {output_tokens}")
        lines.append(f"  Total: {total_tokens}")
        lines.append("")

    return "\n".join(lines)


def prepare_artifacts_dir(
    result: RunResult | dict | object,
    scenario_path: Path,
    scenario_name: str,
) -> Path:
    """Create temporary directory with all artifacts.

    Handles both RunResult (unified) and ScenarioResult (legacy) formats.

    Creates:
        {tmpdir}/
        ├── scenario.yaml     # Original scenario file
        ├── conversation.json # Full message history
        └── summary.txt       # Human-readable summary

    Args:
        result: Run result from scenario execution (any format)
        scenario_path: Path to scenario YAML file
        scenario_name: Human-readable scenario name

    Returns:
        Path to temporary directory (caller must clean up)
    """
    # Create temp directory
    tmpdir = Path(tempfile.mkdtemp(prefix="sandboxy_mlflow_"))

    # Copy scenario YAML
    if scenario_path.exists():
        shutil.copy(scenario_path, tmpdir / "scenario.yaml")

    # Get history from result (handle both formats)
    if isinstance(result, dict):
        history = result.get("history", []) or result.get("messages", [])
        model = result.get("model", "unknown")
    else:
        history = getattr(result, "history", None) or getattr(result, "messages", [])
        model = getattr(result, "model", None) or "unknown"

    # Write conversation.json
    if history:
        # Convert history to serializable format
        serializable_history = []
        for msg in history:
            if hasattr(msg, "model_dump"):
                serializable_history.append(msg.model_dump())
            elif hasattr(msg, "dict"):
                serializable_history.append(msg.dict())
            elif isinstance(msg, dict):
                serializable_history.append(msg)
            else:
                serializable_history.append({"content": str(msg)})

        (tmpdir / "conversation.json").write_text(
            json.dumps(serializable_history, indent=2, default=str)
        )

    # Write summary.txt
    summary = generate_summary(result, scenario_name, model)
    (tmpdir / "summary.txt").write_text(summary)

    return tmpdir
