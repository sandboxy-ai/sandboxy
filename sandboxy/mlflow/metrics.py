"""Metric naming helpers for MLflow integration.

Standardized naming conventions:
- goal_{goal_name}: Individual goal scores (0.0-1.0)
- timing_{phase}_ms: Timing metrics in milliseconds
- tokens_{type}: Token counts (input, output, total)
- score_{category}: Aggregate scores
"""

from __future__ import annotations

import re


def sanitize_metric_name(name: str) -> str:
    """Sanitize a metric name for MLflow compatibility.

    - Converts to lowercase
    - Replaces spaces and special characters with underscores
    - Removes leading/trailing underscores
    - Collapses multiple underscores

    Args:
        name: Raw metric name

    Returns:
        Sanitized metric name safe for MLflow
    """
    # Lowercase
    result = name.lower()
    # Replace spaces and special chars with underscores
    result = re.sub(r"[^a-z0-9_]", "_", result)
    # Collapse multiple underscores
    result = re.sub(r"_+", "_", result)
    # Remove leading/trailing underscores
    result = result.strip("_")
    return result or "unnamed"


def build_goal_metrics(goals: list) -> dict[str, float]:
    """Build metric dict from goal results.

    Args:
        goals: List of GoalResult objects from scenario evaluation

    Returns:
        Dict mapping goal_{goal_name} to score value (1.0 if achieved, 0.0 if not)
    """
    metrics: dict[str, float] = {}
    for goal in goals:
        # Handle both object (GoalResult) and dict formats
        if isinstance(goal, dict):
            name = goal.get("name", goal.get("id", "unnamed"))
            achieved = goal.get("achieved", False)
        else:
            name = getattr(goal, "name", getattr(goal, "id", "unnamed"))
            achieved = getattr(goal, "achieved", False)
        key = f"goal_{sanitize_metric_name(name)}"
        metrics[key] = 1.0 if achieved else 0.0
    return metrics


def build_timing_metrics(latency_ms: int) -> dict[str, float]:
    """Build timing metric dict.

    Args:
        latency_ms: Total execution time in milliseconds

    Returns:
        Dict with timing_total_ms metric
    """
    return {"timing_total_ms": float(latency_ms)}


def build_token_metrics(input_tokens: int, output_tokens: int) -> dict[str, float]:
    """Build token metric dict.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Dict with tokens_input, tokens_output, tokens_total metrics
    """
    return {
        "tokens_input": float(input_tokens),
        "tokens_output": float(output_tokens),
        "tokens_total": float(input_tokens + output_tokens),
    }


def build_score_metrics(
    total_score: float,
    max_score: float,
    percentage: float,
) -> dict[str, float]:
    """Build score metric dict.

    Args:
        total_score: Sum of achieved scores
        max_score: Maximum possible score
        percentage: Percentage achieved (0-100)

    Returns:
        Dict with score_total, score_max, score_percentage metrics
    """
    return {
        "score_total": total_score,
        "score_max": max_score,
        "score_percentage": percentage,
    }
