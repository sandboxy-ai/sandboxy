"""MLflow configuration with CLI > YAML > env precedence resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MLflowConfig:
    """Configuration for MLflow export, resolved from multiple sources.

    Resolution precedence (highest to lowest):
    1. CLI flags (--mlflow-export, --no-mlflow, --mlflow-tracking-uri, --mlflow-experiment)
    2. Scenario YAML mlflow block
    3. Environment variables (MLFLOW_TRACKING_URI)
    4. Defaults
    """

    enabled: bool = False
    tracking_uri: str | None = None
    experiment: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    tracing: bool = True  # Enable LLM call tracing by default when MLflow is enabled

    @classmethod
    def resolve(
        cls,
        cli_export: bool = False,
        cli_no_mlflow: bool = False,
        cli_tracking_uri: str | None = None,
        cli_experiment: str | None = None,
        cli_tracing: bool | None = None,
        yaml_config: dict[str, Any] | None = None,
        scenario_name: str = "default",
    ) -> MLflowConfig:
        """Resolve MLflow configuration with CLI > YAML > env precedence.

        Args:
            cli_export: --mlflow-export flag was set
            cli_no_mlflow: --no-mlflow flag was set (force disable)
            cli_tracking_uri: --mlflow-tracking-uri value
            cli_experiment: --mlflow-experiment value
            cli_tracing: --mlflow-tracing flag (None=use default, True=enable, False=disable)
            yaml_config: mlflow block from scenario YAML
            scenario_name: Fallback experiment name (defaults to scenario name)

        Returns:
            Resolved MLflowConfig instance
        """
        # --no-mlflow always wins
        if cli_no_mlflow:
            return cls(enabled=False)

        yaml_config = yaml_config or {}

        # Determine enabled state: CLI flag or YAML enabled
        yaml_enabled = yaml_config.get("enabled", False)
        enabled = cli_export or yaml_enabled

        if not enabled:
            return cls(enabled=False)

        # Resolve tracking URI: CLI > env > YAML
        tracking_uri = (
            cli_tracking_uri
            or os.environ.get("MLFLOW_TRACKING_URI")
            or yaml_config.get("tracking_uri")
        )

        # Resolve experiment: CLI > YAML > scenario name
        experiment = cli_experiment or yaml_config.get("experiment") or scenario_name

        # Merge custom tags from YAML
        tags = dict(yaml_config.get("tags", {}))

        # Resolve tracing: CLI > YAML > default (True)
        if cli_tracing is not None:
            tracing = cli_tracing
        else:
            tracing = yaml_config.get("tracing", True)

        return cls(
            enabled=True,
            tracking_uri=tracking_uri,
            experiment=experiment,
            tags=tags,
            tracing=tracing,
        )
