"""Tag helpers for MLflow integration.

Standard tags applied to every run:
- sandboxy_version: Package version
- scenario_name: Human-readable scenario name
- scenario_id: Unique scenario identifier
- model_name: Full model name (e.g., openai/gpt-4o)
- model_provider: Provider extracted from model name
- status: success or failed
- agent_name: Agent configuration name

Optional tags:
- commit_hash: Git commit hash (if in repo)
- dataset_case: Dataset case identifier (for benchmarks)
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sandboxy.scenarios.unified import RunResult


def get_sandboxy_version() -> str:
    """Get the current Sandboxy package version.

    Returns:
        Version string or "unknown" if not available
    """
    try:
        from sandboxy import __version__

        return __version__
    except (ImportError, AttributeError):
        # Fallback: try to read from package metadata
        try:
            from importlib.metadata import version

            return version("sandboxy")
        except Exception:
            return "unknown"


def parse_model_provider(model: str) -> str:
    """Extract provider from model string.

    Args:
        model: Model identifier (e.g., "openai/gpt-4o", "anthropic/claude-3")

    Returns:
        Provider name or "unknown" if no provider prefix

    Examples:
        >>> parse_model_provider("openai/gpt-4o")
        'openai'
        >>> parse_model_provider("anthropic/claude-3")
        'anthropic'
        >>> parse_model_provider("gpt-4o")
        'unknown'
    """
    if "/" in model:
        return model.split("/", 1)[0]
    return "unknown"


def get_commit_hash() -> str | None:
    """Get current git commit hash (short form).

    Returns:
        8-character commit hash or None if not in git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except Exception:
        pass
    return None


def build_standard_tags(
    result: RunResult | dict | object,
    scenario_name: str,
    scenario_id: str,
    agent_name: str = "default",
    dataset_case: str | None = None,
) -> dict[str, str]:
    """Build standard tag dict for an MLflow run.

    Handles both RunResult (unified) and ScenarioResult (legacy) formats.

    Args:
        result: Run result from scenario execution (any format)
        scenario_name: Human-readable scenario name
        scenario_id: Unique scenario identifier
        agent_name: Agent configuration name (default: "default")
        dataset_case: Optional dataset case identifier

    Returns:
        Dict of tag name to tag value
    """
    # Extract fields from various result formats
    if isinstance(result, dict):
        error = result.get("error")
        model = result.get("model", "unknown")
    else:
        error = getattr(result, "error", None)
        model = getattr(result, "model", None) or agent_name

    # Determine status
    status = "failed" if error else "success"

    tags = {
        "sandboxy_version": get_sandboxy_version(),
        "scenario_name": scenario_name,
        "scenario_id": scenario_id,
        "model_name": str(model),
        "model_provider": parse_model_provider(str(model)),
        "status": status,
        "agent_name": agent_name,
    }

    # Optional: commit hash
    commit_hash = get_commit_hash()
    if commit_hash:
        tags["commit_hash"] = commit_hash

    # Optional: dataset case
    if dataset_case:
        tags["dataset_case"] = dataset_case

    return tags
