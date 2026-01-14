"""Dataset runner for multi-case benchmarking."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sandboxy.datasets.loader import Dataset, TestCase
from sandboxy.scenarios.unified import (
    RunResult,
    UnifiedRunner,
    UnifiedScenarioSpec,
)

logger = logging.getLogger(__name__)


@dataclass
class CaseResult:
    """Result for a single test case."""

    case_id: str
    expected: list[str] = field(default_factory=list)
    actual_outcome: str | None = None
    passed: bool = False
    goal_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    run_result: RunResult | None = None
    failure_reason: str | None = None
    latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case_id": self.case_id,
            "expected": self.expected,
            "actual_outcome": self.actual_outcome,
            "passed": self.passed,
            "goal_score": self.goal_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "failure_reason": self.failure_reason,
            "latency_ms": self.latency_ms,
            "run_result": self.run_result.to_dict() if self.run_result else None,
        }


@dataclass
class DatasetResult:
    """Aggregated results across all cases."""

    scenario_id: str
    model: str
    dataset_id: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    avg_percentage: float = 0.0
    case_results: list[CaseResult] = field(default_factory=list)
    by_expected: dict[str, dict[str, int]] = field(default_factory=dict)
    total_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "model": self.model,
            "dataset_id": self.dataset_id,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": self.pass_rate,
            "avg_score": self.avg_score,
            "avg_percentage": self.avg_percentage,
            "by_expected": self.by_expected,
            "total_time_ms": self.total_time_ms,
            "case_results": [c.to_dict() for c in self.case_results],
        }

    def format_table(self) -> str:
        """Format results as a table string."""
        lines = [
            f"Dataset Benchmark: {self.scenario_id}",
            f"Model: {self.model}",
            f"Dataset: {self.dataset_id} ({self.total_cases} cases)",
            "",
            "Results Summary",
            "─" * 50,
            f"Passed:     {self.passed_cases}/{self.total_cases} ({self.pass_rate * 100:.1f}%)",
            f"Avg Score:  {self.avg_score:.1f} ({self.avg_percentage:.1f}%)",
            f"Time:       {self.total_time_ms / 1000:.1f}s ({self.total_time_ms / max(self.total_cases, 1):.0f}ms/case)",
        ]

        # By expected outcome
        if self.by_expected:
            lines.append("")
            lines.append("By Expected Outcome:")
            for expected, counts in sorted(self.by_expected.items()):
                total = counts.get("passed", 0) + counts.get("failed", 0)
                passed = counts.get("passed", 0)
                pct = (passed / total * 100) if total > 0 else 0
                lines.append(f"  {expected}: {passed}/{total} ({pct:.1f}%)")

        # Failed cases
        failed = [c for c in self.case_results if not c.passed]
        if failed:
            lines.append("")
            lines.append("Failed Cases:")
            for case in failed[:10]:  # Show first 10 failed
                reason = (
                    case.failure_reason or f"expected {case.expected}, got {case.actual_outcome}"
                )
                lines.append(f"  ✗ {case.case_id}: {reason}")
            if len(failed) > 10:
                lines.append(f"  ... and {len(failed) - 10} more")

        return "\n".join(lines)


async def run_dataset(
    scenario: UnifiedScenarioSpec,
    model: str,
    dataset: Dataset,
    max_turns: int = 20,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> DatasetResult:
    """Run scenario against all test cases in dataset."""
    logger.info(
        "Starting dataset run: scenario=%s, model=%s, dataset=%s, cases=%d",
        scenario.id,
        model,
        dataset.id,
        len(dataset.cases),
    )
    start_time = time.perf_counter()
    runner = UnifiedRunner()
    case_results: list[CaseResult] = []
    by_expected: dict[str, dict[str, int]] = {}

    for case in dataset.cases:
        case_result = await _run_case(
            runner, scenario, model, case, max_turns, max_tokens, temperature
        )
        case_results.append(case_result)

        for exp in case.expected:
            if exp not in by_expected:
                by_expected[exp] = {"passed": 0, "failed": 0}
            if case_result.passed:
                by_expected[exp]["passed"] += 1
            else:
                by_expected[exp]["failed"] += 1

    total_cases = len(case_results)
    passed_cases = sum(1 for c in case_results if c.passed)
    total_score = sum(c.goal_score for c in case_results)
    total_pct = sum(c.percentage for c in case_results)

    total_time_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "Dataset run completed: passed=%d/%d (%.1f%%), time=%dms",
        passed_cases,
        total_cases,
        (passed_cases / total_cases * 100) if total_cases > 0 else 0.0,
        total_time_ms,
    )

    return DatasetResult(
        scenario_id=scenario.id,
        model=model,
        dataset_id=dataset.id,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        pass_rate=passed_cases / total_cases if total_cases > 0 else 0.0,
        avg_score=total_score / total_cases if total_cases > 0 else 0.0,
        avg_percentage=total_pct / total_cases if total_cases > 0 else 0.0,
        case_results=case_results,
        by_expected=by_expected,
        total_time_ms=total_time_ms,
    )


# Known action outcomes that represent final decisions (not process states)
# These are prioritized when determining actual_outcome
ACTION_OUTCOMES = frozenset(
    {
        # Escalation actions
        "sar_filed",
        "aps_referred",
        "hold_placed",
        "alert_cleared",
        # Common action patterns
        "approved",
        "denied",
        "rejected",
        "escalated",
        "flagged",
        "blocked",
        "completed",
        "referred",
    }
)


def _determine_actual_outcome(
    final_state: dict[str, Any],
    scenario: UnifiedScenarioSpec,
    eval_goals: list[Any],
) -> str | None:
    """Determine the actual outcome from run results.

    Priority order:
    1. Scenario-defined outcome goals that were achieved
    2. Known action outcomes from final_state
    3. None if no meaningful outcome found

    Process states like 'checked_user', 'checked_transaction' are excluded
    as they represent investigation steps, not final outcomes.
    """
    # 1. Check scenario-defined outcome goals (most authoritative)
    if scenario.evaluation and scenario.evaluation.goals:
        outcome_goal_ids = {g.id for g in scenario.evaluation.goals if g.outcome}
        for eval_goal in eval_goals:
            if eval_goal.id in outcome_goal_ids and eval_goal.achieved:
                return eval_goal.id

    # 2. Check final_state for known action outcomes
    achieved_actions = [
        key for key, value in final_state.items() if value is True and key in ACTION_OUTCOMES
    ]
    if achieved_actions:
        # Return first achieved action (could also prioritize by a defined order)
        return achieved_actions[0]

    # 3. Check final_state for any custom outcome that looks like an action
    # (ends with _filed, _placed, _referred, _cleared, etc.)
    action_suffixes = ("_filed", "_placed", "_referred", "_cleared", "_approved", "_denied")
    for key, value in final_state.items():
        if value is True and any(key.endswith(suffix) for suffix in action_suffixes):
            return key

    return None


async def _run_case(
    runner: UnifiedRunner,
    scenario: UnifiedScenarioSpec,
    model: str,
    case: TestCase,
    max_turns: int,
    max_tokens: int,
    temperature: float,
) -> CaseResult:
    """Run a single test case."""
    start_time = time.perf_counter()

    try:
        result = await runner.run(
            scenario=scenario,
            model=model,
            variables=case.variables,
            max_turns=max_turns,
            max_tokens=max_tokens,
            temperature=temperature,
            tool_overrides=case.tool_responses,
            expected_outcome=case.expected[0] if case.expected else None,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if result.error:
            return CaseResult(
                case_id=case.id,
                expected=case.expected,
                passed=False,
                failure_reason=f"Run error: {result.error}",
                latency_ms=latency_ms,
            )

        passed = False
        actual_outcome: str | None = None
        failure_reason: str | None = None

        if result.evaluation:
            goal_score = result.evaluation.total_score
            max_score = result.evaluation.max_score
            percentage = result.evaluation.percentage

            final_state = result.final_state or {}

            # Determine actual outcome with proper priority:
            # 1. First, check evaluation goals marked as outcome=true (scenario-defined outcomes)
            # 2. Then check final_state for known action outcomes
            # 3. Process states (checked_*, etc.) are not considered outcomes
            actual_outcome = _determine_actual_outcome(
                final_state=final_state,
                scenario=scenario,
                eval_goals=result.evaluation.goals,
            )

            if case.expected:
                # First check final_state for expected outcomes
                for expected_id in case.expected:
                    if final_state.get(expected_id) is True:
                        passed = True
                        actual_outcome = expected_id
                        break

                # Fallback: check evaluation goals
                if not passed:
                    for expected_id in case.expected:
                        for eval_goal in result.evaluation.goals:
                            if eval_goal.id == expected_id and eval_goal.achieved:
                                passed = True
                                actual_outcome = expected_id
                                break
                        if passed:
                            break

                if not passed:
                    expected_str = " or ".join(case.expected)
                    if actual_outcome:
                        failure_reason = f"expected {expected_str}, got {actual_outcome}"
                    else:
                        failure_reason = f"expected {expected_str}, no outcome achieved"
            else:
                # No expected outcome - pass based on score
                passed = percentage >= 50.0
                if not passed:
                    failure_reason = f"score too low ({percentage:.1f}%)"

            return CaseResult(
                case_id=case.id,
                expected=case.expected,
                actual_outcome=actual_outcome,
                passed=passed,
                goal_score=goal_score,
                max_score=max_score,
                percentage=percentage,
                run_result=result,
                failure_reason=failure_reason,
                latency_ms=latency_ms,
            )
        return CaseResult(
            case_id=case.id,
            expected=case.expected,
            passed=False,
            failure_reason="No evaluation configured",
            run_result=result,
            latency_ms=latency_ms,
        )

    except Exception:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("Exception running case %s", case.id)
        return CaseResult(
            case_id=case.id,
            expected=case.expected,
            passed=False,
            failure_reason="Exception: see logs for details",
            latency_ms=latency_ms,
        )


async def run_dataset_parallel(
    scenario: UnifiedScenarioSpec,
    model: str,
    dataset: Dataset,
    max_turns: int = 20,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    max_concurrent: int = 5,
) -> DatasetResult:
    """Run dataset with parallel case execution."""
    logger.info(
        "Starting parallel dataset run: scenario=%s, model=%s, dataset=%s, cases=%d, concurrency=%d",
        scenario.id,
        model,
        dataset.id,
        len(dataset.cases),
        max_concurrent,
    )
    start_time = time.perf_counter()
    runner = UnifiedRunner()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(case: TestCase) -> CaseResult:
        async with semaphore:
            return await _run_case(
                runner, scenario, model, case, max_turns, max_tokens, temperature
            )

    case_results = await asyncio.gather(*[run_with_semaphore(case) for case in dataset.cases])

    by_expected: dict[str, dict[str, int]] = {}
    for case, case_result in zip(dataset.cases, case_results, strict=True):
        for exp in case.expected:
            if exp not in by_expected:
                by_expected[exp] = {"passed": 0, "failed": 0}
            if case_result.passed:
                by_expected[exp]["passed"] += 1
            else:
                by_expected[exp]["failed"] += 1

    total_cases = len(case_results)
    passed_cases = sum(1 for c in case_results if c.passed)
    total_score = sum(c.goal_score for c in case_results)
    total_pct = sum(c.percentage for c in case_results)

    total_time_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "Parallel dataset run completed: passed=%d/%d (%.1f%%), time=%dms",
        passed_cases,
        total_cases,
        (passed_cases / total_cases * 100) if total_cases > 0 else 0.0,
        total_time_ms,
    )

    return DatasetResult(
        scenario_id=scenario.id,
        model=model,
        dataset_id=dataset.id,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        pass_rate=passed_cases / total_cases if total_cases > 0 else 0.0,
        avg_score=total_score / total_cases if total_cases > 0 else 0.0,
        avg_percentage=total_pct / total_cases if total_cases > 0 else 0.0,
        case_results=list(case_results),
        by_expected=by_expected,
        total_time_ms=total_time_ms,
    )
