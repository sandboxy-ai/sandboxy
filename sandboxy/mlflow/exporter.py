"""MLflow exporter for Sandboxy scenario run results.

This module handles exporting scenario run results to MLflow tracking server.
All methods are designed to be resilient - they log warnings on failure but
never raise exceptions that would crash the scenario run.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sandboxy.mlflow.artifacts import prepare_artifacts_dir
from sandboxy.mlflow.config import MLflowConfig
from sandboxy.mlflow.metrics import (
    build_goal_metrics,
    build_score_metrics,
    build_timing_metrics,
    build_token_metrics,
)
from sandboxy.mlflow.tags import build_standard_tags

if TYPE_CHECKING:
    from sandboxy.scenarios.unified import RunResult

logger = logging.getLogger(__name__)


@contextmanager
def mlflow_run_context(
    config: MLflowConfig,
    run_name: str | None = None,
) -> Generator[str | None, None, None]:
    """Context manager that starts an MLflow run before scenario execution.

    This allows traces from LLM calls to be attached to the run.
    Use this to wrap scenario execution so traces are connected to the run.

    Args:
        config: MLflow configuration
        run_name: Optional name for the run

    Yields:
        The run ID if successful, None otherwise

    Example:
        with mlflow_run_context(config, run_name="gpt-4o") as run_id:
            # Run scenario here - traces will be attached to this run
            result = run_scenario(...)
        # After context exits, log metrics with exporter.log_to_run(run_id, result)
    """
    if not config.enabled:
        yield None
        return

    try:
        import mlflow

        # Setup tracking
        if config.tracking_uri:
            mlflow.set_tracking_uri(config.tracking_uri)
        if config.experiment:
            mlflow.set_experiment(config.experiment)

        # Start run - traces during this context will be attached
        with mlflow.start_run(run_name=run_name) as run:
            yield run.info.run_id

    except ImportError:
        logger.warning("MLflow not installed")
        yield None
    except Exception as e:
        logger.warning(f"Failed to start MLflow run: {e}")
        yield None


class MLflowExporter:
    """Exports Sandboxy run results to MLflow tracking server.

    This exporter is designed to be resilient - it catches all exceptions
    and logs warnings instead of crashing the scenario run. MLflow failures
    should never prevent local results from being saved.
    """

    def __init__(self, config: MLflowConfig) -> None:
        """Initialize exporter with resolved configuration.

        Args:
            config: Resolved MLflowConfig instance
        """
        self.config = config
        self._mlflow = None  # Lazy import

    def _get_mlflow(self):
        """Lazy import mlflow to avoid import errors when not installed."""
        if self._mlflow is None:
            try:
                import mlflow

                self._mlflow = mlflow
            except ImportError as e:
                logger.warning(f"MLflow not installed: {e}")
                return None
        return self._mlflow

    def log_to_active_run(
        self,
        result: dict[str, Any] | Any,
        scenario_path: Path,
        scenario_name: str,
        scenario_id: str,
        agent_name: str = "default",
        dataset_case: str | None = None,
    ) -> bool:
        """Log results to the currently active MLflow run.

        Use this with mlflow_run_context() to connect traces to the run.
        The run should already be started via the context manager.

        Args:
            result: Completed scenario run result (dict or object)
            scenario_path: Path to scenario YAML file
            scenario_name: Human-readable scenario name
            scenario_id: Unique scenario identifier
            agent_name: Agent configuration name
            dataset_case: Optional dataset case identifier

        Returns:
            True on success, False on failure
        """
        if not self.config.enabled:
            return False

        mlflow = self._get_mlflow()
        if mlflow is None:
            return False

        try:
            self._log_parameters(result, scenario_name, scenario_id)
            self._log_metrics(result)
            self._log_tags(
                result,
                scenario_name,
                scenario_id,
                agent_name,
                dataset_case,
            )
            self._log_artifacts(result, scenario_path, scenario_name)
            return True

        except Exception as e:
            logger.warning(f"Failed to log to MLflow run: {e}")
            return False

    def export(
        self,
        result: RunResult,
        scenario_path: Path,
        scenario_name: str,
        scenario_id: str,
        agent_name: str = "default",
        dataset_case: str | None = None,
        run_name: str | None = None,
    ) -> str | None:
        """Export run result to MLflow (creates a new run).

        NOTE: This creates a NEW run. If you want traces connected to the run,
        use mlflow_run_context() + log_to_active_run() instead.

        Args:
            result: Completed scenario run result
            scenario_path: Path to scenario YAML file
            scenario_name: Human-readable scenario name
            scenario_id: Unique scenario identifier
            agent_name: Agent configuration name
            dataset_case: Optional dataset case identifier
            run_name: Optional run name (defaults to "scenario_name - agent_name")

        Returns:
            MLflow run ID on success, None on failure

        Note:
            This method NEVER raises exceptions. All errors are logged
            as warnings and the method returns None.
        """
        if not self.config.enabled:
            return None

        mlflow = self._get_mlflow()
        if mlflow is None:
            return None

        try:
            # Setup tracking
            if not self._setup_tracking():
                return None

            # Generate run name if not provided
            if run_name is None:
                run_name = f"{scenario_name} - {agent_name}"

            # Start run and log everything
            with mlflow.start_run(run_name=run_name) as run:
                run_id = run.info.run_id

                self._log_parameters(result, scenario_name, scenario_id)
                self._log_metrics(result)
                self._log_tags(
                    result,
                    scenario_name,
                    scenario_id,
                    agent_name,
                    dataset_case,
                )
                self._log_artifacts(result, scenario_path, scenario_name)

                return run_id

        except Exception as e:
            logger.warning(f"Failed to export to MLflow: {e}")
            return None

    def _setup_tracking(self) -> bool:
        """Configure MLflow tracking URI and experiment.

        Returns:
            True on success, False on failure
        """
        mlflow = self._get_mlflow()
        if mlflow is None:
            return False

        try:
            if self.config.tracking_uri:
                mlflow.set_tracking_uri(self.config.tracking_uri)

            if self.config.experiment:
                mlflow.set_experiment(self.config.experiment)

            return True
        except Exception as e:
            logger.warning(f"Failed to setup MLflow tracking: {e}")
            return False

    def _log_parameters(
        self,
        result: Any,
        scenario_name: str,
        scenario_id: str,
    ) -> None:
        """Log run parameters to MLflow.

        Args:
            result: Run result (RunResult or ScenarioResult or dict)
            scenario_name: Scenario name
            scenario_id: Scenario ID
        """
        mlflow = self._get_mlflow()
        if mlflow is None:
            return

        try:
            # Handle both RunResult and ScenarioResult formats
            if isinstance(result, dict):
                model = result.get("model", "unknown")
            else:
                model = getattr(result, "model", "unknown")

            mlflow.log_params(
                {
                    "scenario_name": scenario_name,
                    "scenario_id": scenario_id,
                    "model": model,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log parameters to MLflow: {e}")

    def _log_metrics(self, result: Any) -> None:
        """Log all metrics with standardized naming.

        Handles both RunResult (unified) and ScenarioResult (legacy) formats.

        Args:
            result: Run result containing evaluation data
        """
        mlflow = self._get_mlflow()
        if mlflow is None:
            return

        try:
            metrics: dict[str, float] = {}

            # Handle dict format
            if isinstance(result, dict):
                evaluation = result.get("evaluation")
                if evaluation:
                    goals = evaluation.get("goals", [])
                    if goals:
                        metrics.update(build_goal_metrics(goals))
                    metrics.update(
                        build_score_metrics(
                            evaluation.get("total_score", 0),
                            evaluation.get("max_score", 0),
                            evaluation.get("percentage", 0),
                        )
                    )
                # Legacy format - direct score
                elif "score" in result:
                    metrics["score_total"] = float(result.get("score", 0))

                if result.get("latency_ms"):
                    metrics.update(build_timing_metrics(result["latency_ms"]))
                if result.get("input_tokens") or result.get("output_tokens"):
                    metrics.update(
                        build_token_metrics(
                            result.get("input_tokens", 0),
                            result.get("output_tokens", 0),
                        )
                    )
            else:
                # Handle object format (RunResult or ScenarioResult)
                evaluation = getattr(result, "evaluation", None)
                if evaluation:
                    goals = getattr(evaluation, "goals", None)
                    if goals:
                        metrics.update(build_goal_metrics(goals))
                    metrics.update(
                        build_score_metrics(
                            getattr(evaluation, "total_score", 0),
                            getattr(evaluation, "max_score", 0),
                            getattr(evaluation, "percentage", 0),
                        )
                    )
                else:
                    # ScenarioResult format - goal_results and score at top level
                    goal_results = getattr(result, "goal_results", None)
                    if goal_results:
                        metrics.update(build_goal_metrics(goal_results))

                    score = getattr(result, "score", 0) or 0
                    max_score = getattr(result, "max_score", 0) or 0
                    percentage = (score / max_score * 100) if max_score > 0 else 0
                    metrics.update(build_score_metrics(score, max_score, percentage))

                latency = getattr(result, "latency_ms", None)
                if latency:
                    metrics.update(build_timing_metrics(latency))

                input_tokens = getattr(result, "input_tokens", 0) or 0
                output_tokens = getattr(result, "output_tokens", 0) or 0
                if input_tokens or output_tokens:
                    metrics.update(build_token_metrics(input_tokens, output_tokens))

            if metrics:
                mlflow.log_metrics(metrics)

        except Exception as e:
            logger.warning(f"Failed to log metrics to MLflow: {e}")

    def _log_tags(
        self,
        result: Any,
        scenario_name: str,
        scenario_id: str,
        agent_name: str = "default",
        dataset_case: str | None = None,
    ) -> None:
        """Log all tags including custom tags from config.

        Args:
            result: Run result (RunResult, ScenarioResult, or dict)
            scenario_name: Scenario name
            scenario_id: Scenario ID
            agent_name: Agent configuration name
            dataset_case: Optional dataset case identifier
        """
        mlflow = self._get_mlflow()
        if mlflow is None:
            return

        try:
            # Build standard tags
            tags = build_standard_tags(
                result=result,
                scenario_name=scenario_name,
                scenario_id=scenario_id,
                agent_name=agent_name,
                dataset_case=dataset_case,
            )

            # Merge custom tags from config (config tags take precedence)
            tags.update(self.config.tags)

            mlflow.set_tags(tags)

        except Exception as e:
            logger.warning(f"Failed to log tags to MLflow: {e}")

    def _log_artifacts(
        self,
        result: Any,
        scenario_path: Path,
        scenario_name: str,
    ) -> None:
        """Generate and upload artifacts.

        Uploads:
        - scenario.yaml: Original scenario file
        - conversation.json: Full message history
        - summary.txt: Human-readable summary

        Args:
            result: Run result
            scenario_path: Path to scenario YAML
            scenario_name: Scenario name
        """
        mlflow = self._get_mlflow()
        if mlflow is None:
            return

        artifacts_dir = None
        try:
            # Prepare artifacts directory
            artifacts_dir = prepare_artifacts_dir(
                result=result,
                scenario_path=scenario_path,
                scenario_name=scenario_name,
            )

            # Log all artifacts
            mlflow.log_artifacts(str(artifacts_dir))

        except Exception as e:
            logger.warning(f"Failed to log artifacts to MLflow: {e}")

        finally:
            # Cleanup temp directory
            if artifacts_dir and artifacts_dir.exists():
                import shutil

                shutil.rmtree(artifacts_dir, ignore_errors=True)
