"""Comparison utilities for multi-model scenario runs.

This module provides:
- ComparisonResult: Aggregates results from multiple models
- Statistical summaries (avg, min, max, std)
- Tabular and JSON output formatting
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sandboxy.scenarios.unified import RunResult, UnifiedScenarioSpec

logger = logging.getLogger(__name__)


@dataclass
class ModelStats:
    """Statistics for a single model across multiple runs."""

    model: str
    runs: int = 0
    avg_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    std_score: float = 0.0
    avg_latency_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float | None = None
    avg_cost_usd: float | None = None
    errors: int = 0

    # Message/turn counts
    total_messages: int = 0
    avg_messages: float = 0.0
    total_tool_calls: int = 0
    avg_tool_calls: float = 0.0

    # Goal achievements (percentage of runs that achieved each goal)
    goal_rates: dict[str, float] = field(default_factory=dict)

    # Judge scores (if applicable)
    avg_judge_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "runs": self.runs,
            "avg_score": self.avg_score,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "std_score": self.std_score,
            "avg_latency_ms": self.avg_latency_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "avg_cost_usd": self.avg_cost_usd,
            "total_messages": self.total_messages,
            "avg_messages": self.avg_messages,
            "total_tool_calls": self.total_tool_calls,
            "avg_tool_calls": self.avg_tool_calls,
            "errors": self.errors,
            "goal_rates": self.goal_rates,
            "avg_judge_score": self.avg_judge_score,
        }


@dataclass
class ComparisonResult:
    """Result of running a scenario with multiple models.

    Aggregates results from all runs and provides statistical summaries.
    """

    scenario_id: str
    scenario_name: str
    models: list[str]
    runs_per_model: int
    results: list[RunResult] = field(default_factory=list)
    stats: dict[str, ModelStats] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    # Cached ranking
    _ranking: list[str] | None = field(default=None, repr=False)

    def add_result(self, result: RunResult) -> None:
        """Add a result and update statistics."""
        self.results.append(result)
        self._ranking = None  # Invalidate cache

    def compute_stats(self) -> None:
        """Compute statistics for all models."""
        # Import pricing calculator
        try:
            from sandboxy.api.routes.local import calculate_cost
        except ImportError:
            calculate_cost = None  # type: ignore

        # Group results by model
        by_model: dict[str, list[RunResult]] = {}
        for result in self.results:
            if result.model not in by_model:
                by_model[result.model] = []
            by_model[result.model].append(result)

        # Compute stats for each model
        for model, model_results in by_model.items():
            scores = []
            latencies = []
            input_tokens = 0
            output_tokens = 0
            costs: list[float] = []
            errors = 0
            goal_achievements: dict[str, list[bool]] = {}
            judge_scores: list[float] = []
            message_counts: list[int] = []
            tool_call_counts: list[int] = []

            for result in model_results:
                if result.error:
                    errors += 1
                    continue

                # Collect scores
                if result.evaluation:
                    scores.append(result.evaluation.total_score)

                    # Collect goal achievements
                    for goal in result.evaluation.goals:
                        if goal.id not in goal_achievements:
                            goal_achievements[goal.id] = []
                        goal_achievements[goal.id].append(goal.achieved)

                    # Collect judge scores
                    if result.evaluation.judge:
                        judge_scores.append(result.evaluation.judge.score)

                latencies.append(result.latency_ms)
                input_tokens += result.input_tokens
                output_tokens += result.output_tokens

                # Collect cost (from API or calculate from tokens)
                if result.cost_usd is not None:
                    costs.append(result.cost_usd)
                elif calculate_cost and result.input_tokens and result.output_tokens:
                    calculated = calculate_cost(model, result.input_tokens, result.output_tokens)
                    if calculated is not None:
                        costs.append(calculated)

                # Count messages (history length)
                if result.history:
                    message_counts.append(len(result.history))

                # Count tool calls
                if result.tool_calls:
                    tool_call_counts.append(len(result.tool_calls))
                else:
                    tool_call_counts.append(0)

            # Calculate statistics
            stats = ModelStats(
                model=model,
                runs=len(model_results),
                errors=errors,
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
                total_cost_usd=sum(costs) if costs else None,
                avg_cost_usd=statistics.mean(costs) if costs else None,
                total_messages=sum(message_counts),
                avg_messages=statistics.mean(message_counts) if message_counts else 0.0,
                total_tool_calls=sum(tool_call_counts),
                avg_tool_calls=statistics.mean(tool_call_counts) if tool_call_counts else 0.0,
            )

            if scores:
                stats.avg_score = statistics.mean(scores)
                stats.min_score = min(scores)
                stats.max_score = max(scores)
                stats.std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0

            if latencies:
                stats.avg_latency_ms = int(statistics.mean(latencies))

            if judge_scores:
                stats.avg_judge_score = statistics.mean(judge_scores)

            # Calculate goal rates
            for goal_id, achievements in goal_achievements.items():
                stats.goal_rates[goal_id] = sum(achievements) / len(achievements) * 100

            self.stats[model] = stats

    def get_ranking(self) -> list[str]:
        """Get models ranked by average score (highest first)."""
        if self._ranking is not None:
            return self._ranking

        if not self.stats:
            self.compute_stats()

        self._ranking = sorted(
            self.stats.keys(),
            key=lambda m: self.stats[m].avg_score,
            reverse=True,
        )
        return self._ranking

    def get_winner(self) -> str | None:
        """Get the model with highest average score."""
        ranking = self.get_ranking()
        return ranking[0] if ranking else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        if not self.stats:
            self.compute_stats()

        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "models": self.models,
            "runs_per_model": self.runs_per_model,
            "results": [r.to_dict() for r in self.results],
            "stats": {k: v.to_dict() for k, v in self.stats.items()},
            "ranking": self.get_ranking(),
            "winner": self.get_winner(),
            "created_at": self.created_at.isoformat(),
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=indent)

    def to_table(self, max_goals: int = 5) -> str:
        """Format as ASCII table.

        Args:
            max_goals: Maximum number of goals to show in table

        Returns:
            Formatted table string

        """
        if not self.stats:
            self.compute_stats()

        lines = [
            f"Model Comparison: {self.scenario_name}",
            f"Runs per model: {self.runs_per_model}",
            "",
        ]

        # Collect all goal IDs
        all_goals: set[str] = set()
        for stats in self.stats.values():
            all_goals.update(stats.goal_rates.keys())
        goal_ids = sorted(all_goals)[:max_goals]

        # Build header
        headers = ["Model", "Avg Score", "Latency", "Messages", "Tools", "Cost"]
        if goal_ids:
            headers.extend(goal_ids)
        if any(s.avg_judge_score is not None for s in self.stats.values()):
            headers.append("Judge")

        # Calculate column widths
        rows: list[list[str]] = []
        for model in self.get_ranking():
            stats = self.stats[model]
            # Format cost
            if stats.avg_cost_usd is not None:
                if stats.avg_cost_usd < 0.01:
                    cost_str = f"${stats.avg_cost_usd:.4f}"
                else:
                    cost_str = f"${stats.avg_cost_usd:.3f}"
            else:
                cost_str = "-"

            row = [
                model[:30],  # Truncate long model names
                f"{stats.avg_score:.1f}",
                f"{stats.avg_latency_ms}ms",
                f"{stats.avg_messages:.1f}",
                f"{stats.avg_tool_calls:.1f}",
                cost_str,
            ]

            # Add goal rates
            for goal_id in goal_ids:
                rate = stats.goal_rates.get(goal_id, 0)
                row.append(f"{rate:.0f}%")

            # Add judge score
            if any(s.avg_judge_score is not None for s in self.stats.values()):
                if stats.avg_judge_score is not None:
                    row.append(f"{stats.avg_judge_score:.2f}")
                else:
                    row.append("-")

            rows.append(row)

        # Calculate column widths
        widths = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

        # Build table
        sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

        lines.append(sep)
        lines.append("|" + "|".join(f" {h.ljust(widths[i])} " for i, h in enumerate(headers)) + "|")
        lines.append(sep)

        for row in rows:
            lines.append("|" + "|".join(f" {c.ljust(widths[i])} " for i, c in enumerate(row)) + "|")

        lines.append(sep)

        # Add summary
        if self.stats:
            winner = self.get_winner()
            if winner:
                lines.append("")
                lines.append(f"Winner: {winner}")

        return "\n".join(lines)

    def to_markdown(self, max_goals: int = 5) -> str:
        """Format as Markdown table.

        Args:
            max_goals: Maximum number of goals to show

        Returns:
            Markdown formatted string

        """
        if not self.stats:
            self.compute_stats()

        lines = [
            f"## Model Comparison: {self.scenario_name}",
            "",
            f"Runs per model: {self.runs_per_model}",
            "",
        ]

        # Collect all goal IDs
        all_goals: set[str] = set()
        for stats in self.stats.values():
            all_goals.update(stats.goal_rates.keys())
        goal_ids = sorted(all_goals)[:max_goals]

        # Build header
        headers = ["Model", "Avg Score", "Latency", "Msgs", "Tools", "Cost"]
        if goal_ids:
            headers.extend(goal_ids)
        if any(s.avg_judge_score is not None for s in self.stats.values()):
            headers.append("Judge")

        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("-" * len(h) for h in headers) + " |")

        for model in self.get_ranking():
            stats = self.stats[model]
            # Format cost
            if stats.avg_cost_usd is not None:
                if stats.avg_cost_usd < 0.01:
                    cost_str = f"${stats.avg_cost_usd:.4f}"
                else:
                    cost_str = f"${stats.avg_cost_usd:.3f}"
            else:
                cost_str = "-"

            row = [
                f"`{model}`",
                f"{stats.avg_score:.1f}",
                f"{stats.avg_latency_ms}ms",
                f"{stats.avg_messages:.1f}",
                f"{stats.avg_tool_calls:.1f}",
                cost_str,
            ]

            for goal_id in goal_ids:
                rate = stats.goal_rates.get(goal_id, 0)
                row.append(f"{rate:.0f}%")

            if any(s.avg_judge_score is not None for s in self.stats.values()):
                if stats.avg_judge_score is not None:
                    row.append(f"{stats.avg_judge_score:.2f}")
                else:
                    row.append("-")

            lines.append("| " + " | ".join(row) + " |")

        # Add winner
        winner = self.get_winner()
        if winner:
            lines.append("")
            lines.append(f"**Winner:** `{winner}`")

        return "\n".join(lines)

    def pretty(self) -> str:
        """Format for human-readable display (alias for to_table)."""
        return self.to_table()


async def run_comparison(
    scenario: UnifiedScenarioSpec,
    models: list[str],
    runs_per_model: int = 1,
    variables: dict[str, Any] | None = None,
    max_turns: int = 20,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    parallel: bool = True,
) -> ComparisonResult:
    """Run a scenario with multiple models and compare results.

    Args:
        scenario: The scenario specification
        models: List of model IDs to test
        runs_per_model: Number of runs per model (for statistical significance)
        variables: Variable substitutions
        max_turns: Maximum conversation turns
        max_tokens: Maximum tokens per response
        temperature: Sampling temperature
        parallel: Run models in parallel (True) or sequentially (False)

    Returns:
        ComparisonResult with all runs and statistics

    """
    import asyncio

    from sandboxy.scenarios.unified import UnifiedRunner

    runner = UnifiedRunner()
    comparison = ComparisonResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name or scenario.id,
        models=models,
        runs_per_model=runs_per_model,
    )

    async def run_single(model: str) -> RunResult:
        """Run a single model iteration."""
        return await runner.run(
            scenario=scenario,
            model=model,
            variables=variables,
            max_turns=max_turns,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    if parallel:
        # Run ALL iterations for ALL models in parallel
        # Creates [(model, task), ...] for every model × runs_per_model
        tasks = [run_single(model) for model in models for _ in range(runs_per_model)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other results
                logger.error(f"Run failed: {result}")
            else:
                comparison.add_result(result)
    else:
        # Run sequentially
        for model in models:
            for _ in range(runs_per_model):
                result = await runner.run(
                    scenario=scenario,
                    model=model,
                    variables=variables,
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                comparison.add_result(result)

    comparison.compute_stats()
    return comparison
