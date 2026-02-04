"""Tests for MLflow artifact helpers."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from sandboxy.mlflow.artifacts import generate_summary, prepare_artifacts_dir


class TestGenerateSummary:
    """Test summary generation."""

    def create_mock_result(
        self,
        model="openai/gpt-4o",
        error=None,
        goals=None,
        total_score=0.0,
        max_score=0.0,
        percentage=0.0,
        latency_ms=1000,
        input_tokens=100,
        output_tokens=50,
    ):
        """Create a mock RunResult."""
        result = MagicMock()
        result.model = model
        result.error = error
        result.latency_ms = latency_ms
        result.input_tokens = input_tokens
        result.output_tokens = output_tokens

        # Mock evaluation
        result.evaluation = MagicMock()
        result.evaluation.goals = goals or []
        result.evaluation.total_score = total_score
        result.evaluation.max_score = max_score
        result.evaluation.percentage = percentage

        return result

    def test_includes_header(self):
        """Summary includes header."""
        result = self.create_mock_result()
        summary = generate_summary(result, "Test Scenario", "openai/gpt-4o")
        assert "Sandboxy Run Summary" in summary

    def test_includes_scenario_name(self):
        """Summary includes scenario name."""
        result = self.create_mock_result()
        summary = generate_summary(result, "My Test Scenario", "gpt-4o")
        assert "My Test Scenario" in summary

    def test_includes_model(self):
        """Summary includes model name."""
        result = self.create_mock_result(model="anthropic/claude-3")
        summary = generate_summary(result, "Test", "anthropic/claude-3")
        assert "anthropic/claude-3" in summary

    def test_status_passed(self):
        """Shows PASSED when no error."""
        result = self.create_mock_result(error=None)
        summary = generate_summary(result, "Test", "gpt-4o")
        assert "PASSED" in summary

    def test_status_failed(self):
        """Shows FAILED when error present."""
        result = self.create_mock_result(error="Something went wrong")
        summary = generate_summary(result, "Test", "gpt-4o")
        assert "FAILED" in summary

    def test_includes_goals(self):
        """Summary includes goal scores."""
        goal1 = MagicMock()
        goal1.name = "goal_one"
        goal1.score = 1.0
        goal1.passed = True

        goal2 = MagicMock()
        goal2.name = "goal_two"
        goal2.score = 0.5
        goal2.passed = False

        result = self.create_mock_result(
            goals=[goal1, goal2],
            total_score=1.5,
            max_score=2.0,
            percentage=75.0,
        )
        summary = generate_summary(result, "Test", "gpt-4o")

        assert "goal_one" in summary
        assert "goal_two" in summary

    def test_includes_timing(self):
        """Summary includes timing information."""
        result = self.create_mock_result(latency_ms=1234)
        summary = generate_summary(result, "Test", "gpt-4o")
        assert "1234" in summary

    def test_includes_tokens(self):
        """Summary includes token counts."""
        result = self.create_mock_result(input_tokens=450, output_tokens=120)
        summary = generate_summary(result, "Test", "gpt-4o")
        assert "450" in summary
        assert "120" in summary
        assert "570" in summary  # total


class TestPrepareArtifactsDir:
    """Test artifact directory preparation."""

    def create_mock_result(self, history=None):
        """Create a mock RunResult with history."""
        result = MagicMock()
        result.model = "gpt-4o"
        result.error = None
        result.latency_ms = 1000
        result.input_tokens = 100
        result.output_tokens = 50

        result.evaluation = MagicMock()
        result.evaluation.goals = []
        result.evaluation.total_score = 0.0
        result.evaluation.max_score = 0.0
        result.evaluation.percentage = 0.0

        # History for conversation.json
        if history is None:
            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        result.history = history

        return result

    def test_creates_summary_txt(self):
        """Creates summary.txt artifact."""
        result = self.create_mock_result()

        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"id: test\nname: Test")
            scenario_path = Path(f.name)

        try:
            artifacts_dir = prepare_artifacts_dir(result, scenario_path, "Test")
            summary_path = artifacts_dir / "summary.txt"

            assert summary_path.exists()
            content = summary_path.read_text()
            assert "Sandboxy Run Summary" in content
        finally:
            scenario_path.unlink()
            # Cleanup artifacts dir
            import shutil

            shutil.rmtree(artifacts_dir, ignore_errors=True)

    def test_creates_conversation_json(self):
        """Creates conversation.json artifact."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        result = self.create_mock_result(history=history)

        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"id: test\nname: Test")
            scenario_path = Path(f.name)

        try:
            artifacts_dir = prepare_artifacts_dir(result, scenario_path, "Test")
            conv_path = artifacts_dir / "conversation.json"

            assert conv_path.exists()
            content = json.loads(conv_path.read_text())
            assert len(content) == 2
            assert content[0]["role"] == "user"
        finally:
            scenario_path.unlink()
            import shutil

            shutil.rmtree(artifacts_dir, ignore_errors=True)

    def test_copies_scenario_yaml(self):
        """Copies scenario YAML to artifacts."""
        result = self.create_mock_result()

        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"id: test\nname: Test Scenario")
            scenario_path = Path(f.name)

        try:
            artifacts_dir = prepare_artifacts_dir(result, scenario_path, "Test")
            copied_path = artifacts_dir / "scenario.yaml"

            assert copied_path.exists()
            content = copied_path.read_text()
            assert "Test Scenario" in content
        finally:
            scenario_path.unlink()
            import shutil

            shutil.rmtree(artifacts_dir, ignore_errors=True)
