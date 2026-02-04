"""Tests for MLflowConfig resolution logic."""

import os
from unittest.mock import patch

from sandboxy.mlflow.config import MLflowConfig


class TestMLflowConfigResolve:
    """Test MLflowConfig.resolve() precedence logic."""

    def test_disabled_by_default(self):
        """Config is disabled when no flags are set."""
        config = MLflowConfig.resolve()
        assert config.enabled is False

    def test_no_mlflow_flag_always_wins(self):
        """--no-mlflow disables even when YAML enables."""
        config = MLflowConfig.resolve(
            cli_no_mlflow=True,
            cli_export=True,
            yaml_config={"enabled": True},
        )
        assert config.enabled is False

    def test_cli_export_enables(self):
        """--mlflow-export enables export."""
        config = MLflowConfig.resolve(cli_export=True, scenario_name="test")
        assert config.enabled is True
        assert config.experiment == "test"

    def test_yaml_enabled_enables(self):
        """YAML enabled: true enables export."""
        config = MLflowConfig.resolve(
            yaml_config={"enabled": True},
            scenario_name="test",
        )
        assert config.enabled is True

    def test_tracking_uri_precedence_cli_first(self):
        """CLI tracking URI takes precedence over env and YAML."""
        with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "env://uri"}):
            config = MLflowConfig.resolve(
                cli_export=True,
                cli_tracking_uri="cli://uri",
                yaml_config={"tracking_uri": "yaml://uri"},
            )
            assert config.tracking_uri == "cli://uri"

    def test_tracking_uri_precedence_env_second(self):
        """Env variable takes precedence over YAML."""
        with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "env://uri"}):
            config = MLflowConfig.resolve(
                cli_export=True,
                yaml_config={"tracking_uri": "yaml://uri"},
            )
            assert config.tracking_uri == "env://uri"

    def test_tracking_uri_precedence_yaml_third(self):
        """YAML tracking URI used when no CLI or env."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing MLFLOW_TRACKING_URI
            os.environ.pop("MLFLOW_TRACKING_URI", None)
            config = MLflowConfig.resolve(
                cli_export=True,
                yaml_config={"tracking_uri": "yaml://uri"},
            )
            assert config.tracking_uri == "yaml://uri"

    def test_experiment_precedence_cli_first(self):
        """CLI experiment takes precedence over YAML and scenario name."""
        config = MLflowConfig.resolve(
            cli_export=True,
            cli_experiment="cli-exp",
            yaml_config={"experiment": "yaml-exp"},
            scenario_name="scenario-name",
        )
        assert config.experiment == "cli-exp"

    def test_experiment_precedence_yaml_second(self):
        """YAML experiment takes precedence over scenario name."""
        config = MLflowConfig.resolve(
            cli_export=True,
            yaml_config={"experiment": "yaml-exp"},
            scenario_name="scenario-name",
        )
        assert config.experiment == "yaml-exp"

    def test_experiment_defaults_to_scenario_name(self):
        """Experiment defaults to scenario name."""
        config = MLflowConfig.resolve(
            cli_export=True,
            scenario_name="my-scenario",
        )
        assert config.experiment == "my-scenario"

    def test_custom_tags_from_yaml(self):
        """Custom tags are copied from YAML config."""
        config = MLflowConfig.resolve(
            cli_export=True,
            yaml_config={
                "tags": {
                    "team": "support",
                    "env": "staging",
                }
            },
        )
        assert config.tags == {"team": "support", "env": "staging"}

    def test_empty_yaml_config(self):
        """Empty YAML config doesn't cause errors."""
        config = MLflowConfig.resolve(
            cli_export=True,
            yaml_config={},
            scenario_name="test",
        )
        assert config.enabled is True
        assert config.tags == {}

    def test_none_yaml_config(self):
        """None YAML config doesn't cause errors."""
        config = MLflowConfig.resolve(
            cli_export=True,
            yaml_config=None,
            scenario_name="test",
        )
        assert config.enabled is True
