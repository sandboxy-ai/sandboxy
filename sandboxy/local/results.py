"""Local results storage for Sandboxy runs.

This module provides functions for persisting, retrieving, and managing
scenario run results in the local runs/ directory. Results are stored
as JSON files with timestamps for easy tracking and analysis.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sandboxy.local.context import get_local_context

logger = logging.getLogger(__name__)


def save_run_result(
    scenario_id: str,
    result: dict[str, Any] | Any,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Save a run result to the local runs/ directory.

    Args:
        scenario_id: Identifier for the scenario that was run.
        result: The result data to save. If it has a to_dict() method, it will be called.
        metadata: Optional additional metadata to include.

    Returns:
        Path to the saved result file.

    Raises:
        RuntimeError: If not in local mode.

    """
    ctx = get_local_context()
    if not ctx:
        raise RuntimeError("Not in local mode - cannot save results")

    # Ensure runs directory exists
    ctx.runs_dir.mkdir(exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scenario_id}_{timestamp}.json"
    filepath = ctx.runs_dir / filename

    # Convert result to dict if needed
    if hasattr(result, "to_dict"):
        result_data = result.to_dict()
    elif hasattr(result, "__dict__"):
        result_data = result.__dict__
    else:
        result_data = result

    # Build output structure
    output = {
        "scenario_id": scenario_id,
        "timestamp": datetime.now().isoformat(),
        "result": result_data,
        "metadata": metadata or {},
    }

    # Write to file
    filepath.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Saved run result to %s", filepath)

    return filepath


def list_run_results(
    limit: int = 100,
    scenario_id: str | None = None,
) -> list[dict[str, Any]]:
    """List run results from the local runs/ directory.

    Args:
        limit: Maximum number of results to return.
        scenario_id: Optional filter by scenario ID.

    Returns:
        List of run result summaries, most recent first.

    """
    ctx = get_local_context()
    if not ctx:
        return []

    if not ctx.runs_dir.exists():
        return []

    results = []
    for path in sorted(ctx.runs_dir.glob("*.json"), reverse=True):
        if len(results) >= limit:
            break

        try:
            data = json.loads(path.read_text())

            # Filter by scenario_id if specified
            if scenario_id and data.get("scenario_id") != scenario_id:
                continue

            results.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "scenario_id": data.get("scenario_id"),
                    "timestamp": data.get("timestamp"),
                    "metadata": data.get("metadata", {}),
                }
            )
        except Exception as e:
            logger.warning("Failed to read run result %s: %s", path, e)
            continue

    return results


def get_run_result(filename: str) -> dict[str, Any] | None:
    """Get a specific run result by filename.

    Args:
        filename: The filename of the run result.

    Returns:
        The full run result data, or None if not found.

    """
    ctx = get_local_context()
    if not ctx:
        return None

    filepath = ctx.runs_dir / filename
    if not filepath.exists():
        return None

    try:
        return json.loads(filepath.read_text())
    except Exception as e:
        logger.warning("Failed to read run result %s: %s", filepath, e)
        return None


def delete_run_result(filename: str) -> bool:
    """Delete a run result by filename.

    Args:
        filename: The filename of the run result to delete.

    Returns:
        True if deleted, False if not found or error.

    """
    ctx = get_local_context()
    if not ctx:
        return False

    filepath = ctx.runs_dir / filename
    if not filepath.exists():
        return False

    try:
        filepath.unlink()
        logger.info("Deleted run result %s", filepath)
        return True
    except Exception as e:
        logger.warning("Failed to delete run result %s: %s", filepath, e)
        return False
