"""Integration tests for MLflow export functionality.

These tests verify the complete MLflow export workflow with mocked MLflow server.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMLflowExporterIntegration:
    """Integration tests for MLflowExporter."""

    def create_mock_result(self):
        """Create a mock RunResult with realistic data."""
        result = MagicMock()
        result.model = "openai/gpt-4o"
        result.error = None
        result.latency_ms = 1234
        result.input_tokens = 450
        result.output_tokens = 120

        # Mock evaluation
        goal1 = MagicMock()
        goal1.name = "acknowledged_request"
        goal1.score = 1.0
        goal1.passed = True

        goal2 = MagicMock()
        goal2.name = "used_tool"
        goal2.score = 0.8
        goal2.passed = True

        result.evaluation = MagicMock()
        result.evaluation.goals = [goal1, goal2]
        result.evaluation.total_score = 1.8
        result.evaluation.max_score = 2.0
        result.evaluation.percentage = 90.0

        # Mock history
        result.history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        return result

    @patch("sandboxy.mlflow.exporter.MLflowExporter._get_mlflow")
    def test_export_logs_all_components(self, mock_get_mlflow):
        """Export logs parameters, metrics, tags, and artifacts."""
        from sandboxy.mlflow.config import MLflowConfig
        from sandboxy.mlflow.exporter import MLflowExporter

        # Mock MLflow
        mock_mlflow = MagicMock()
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id-123"
        mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=None)
        mock_get_mlflow.return_value = mock_mlflow

        config = MLflowConfig(
            enabled=True,
            tracking_uri="http://localhost:5000",
            experiment="test-experiment",
            tags={"custom": "tag"},
        )
        exporter = MLflowExporter(config)
        result = self.create_mock_result()

        # Create temp scenario file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"id: test\nname: Test Scenario")
            scenario_path = Path(f.name)

        try:
            run_id = exporter.export(
                result=result,
                scenario_path=scenario_path,
                scenario_name="Test Scenario",
                scenario_id="test-scenario",
            )

            # Verify run ID returned
            assert run_id == "test-run-id-123"

            # Verify tracking setup
            mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")
            mock_mlflow.set_experiment.assert_called_once_with("test-experiment")

            # Verify parameters logged
            mock_mlflow.log_params.assert_called()

            # Verify metrics logged
            mock_mlflow.log_metrics.assert_called()

            # Verify tags set
            mock_mlflow.set_tags.assert_called()

            # Verify artifacts logged
            mock_mlflow.log_artifacts.assert_called()

        finally:
            scenario_path.unlink()

    @patch("sandboxy.mlflow.exporter.MLflowExporter._get_mlflow")
    def test_export_handles_mlflow_unavailable(self, mock_get_mlflow):
        """Export returns None when MLflow is not available."""
        from sandboxy.mlflow.config import MLflowConfig
        from sandboxy.mlflow.exporter import MLflowExporter

        mock_get_mlflow.return_value = None

        config = MLflowConfig(enabled=True)
        exporter = MLflowExporter(config)
        result = self.create_mock_result()

        run_id = exporter.export(
            result=result,
            scenario_path=Path("test.yml"),
            scenario_name="Test",
            scenario_id="test",
        )

        assert run_id is None

    @patch("sandboxy.mlflow.exporter.MLflowExporter._get_mlflow")
    def test_export_handles_connection_error(self, mock_get_mlflow):
        """Export handles connection errors gracefully."""
        from sandboxy.mlflow.config import MLflowConfig
        from sandboxy.mlflow.exporter import MLflowExporter

        # Mock MLflow that raises on set_tracking_uri
        mock_mlflow = MagicMock()
        mock_mlflow.set_tracking_uri.side_effect = ConnectionError("Server unavailable")
        mock_get_mlflow.return_value = mock_mlflow

        config = MLflowConfig(
            enabled=True,
            tracking_uri="http://unavailable:5000",
        )
        exporter = MLflowExporter(config)
        result = self.create_mock_result()

        # Should not raise, should return None
        run_id = exporter.export(
            result=result,
            scenario_path=Path("test.yml"),
            scenario_name="Test",
            scenario_id="test",
        )

        assert run_id is None

    @patch("sandboxy.mlflow.exporter.MLflowExporter._get_mlflow")
    def test_export_continues_on_partial_failure(self, mock_get_mlflow):
        """Export continues logging other data when one component fails."""
        from sandboxy.mlflow.config import MLflowConfig
        from sandboxy.mlflow.exporter import MLflowExporter

        # Mock MLflow that fails on metrics but succeeds elsewhere
        mock_mlflow = MagicMock()
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id"
        mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=None)
        mock_mlflow.log_metrics.side_effect = Exception("Metrics failed")
        mock_get_mlflow.return_value = mock_mlflow

        config = MLflowConfig(enabled=True)
        exporter = MLflowExporter(config)
        result = self.create_mock_result()

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"id: test")
            scenario_path = Path(f.name)

        try:
            run_id = exporter.export(
                result=result,
                scenario_path=scenario_path,
                scenario_name="Test",
                scenario_id="test",
            )

            # Should still return run_id despite metrics failure
            assert run_id == "test-run-id"

            # Params and tags should still be called
            mock_mlflow.log_params.assert_called()
            mock_mlflow.set_tags.assert_called()

        finally:
            scenario_path.unlink()

    def test_disabled_export_returns_none(self):
        """Export returns None immediately when disabled."""
        from sandboxy.mlflow.config import MLflowConfig
        from sandboxy.mlflow.exporter import MLflowExporter

        config = MLflowConfig(enabled=False)
        exporter = MLflowExporter(config)
        result = self.create_mock_result()

        run_id = exporter.export(
            result=result,
            scenario_path=Path("test.yml"),
            scenario_name="Test",
            scenario_id="test",
        )

        assert run_id is None


@pytest.mark.integration
class TestMLflowConfigIntegration:
    """Integration tests for MLflowConfig resolution."""

    def test_full_config_resolution(self):
        """Test complete config resolution with all sources."""
        import os

        from sandboxy.mlflow.config import MLflowConfig

        # Set env variable
        with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "env://uri"}):
            config = MLflowConfig.resolve(
                cli_export=True,
                cli_tracking_uri="cli://uri",  # Should win
                yaml_config={
                    "experiment": "yaml-experiment",
                    "tags": {"team": "test"},
                },
                scenario_name="scenario-name",
            )

            assert config.enabled is True
            assert config.tracking_uri == "cli://uri"  # CLI wins
            assert config.experiment == "yaml-experiment"  # YAML used
            assert config.tags == {"team": "test"}
