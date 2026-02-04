"""Tests for MLflow metric naming helpers."""

from unittest.mock import MagicMock

from sandboxy.mlflow.metrics import (
    build_goal_metrics,
    build_score_metrics,
    build_timing_metrics,
    build_token_metrics,
    sanitize_metric_name,
)


class TestSanitizeMetricName:
    """Test metric name sanitization."""

    def test_lowercase(self):
        """Converts to lowercase."""
        assert sanitize_metric_name("MyMetric") == "mymetric"

    def test_replace_spaces(self):
        """Replaces spaces with underscores."""
        assert sanitize_metric_name("my metric") == "my_metric"

    def test_replace_special_chars(self):
        """Replaces special characters with underscores."""
        assert sanitize_metric_name("my-metric.v2") == "my_metric_v2"

    def test_collapse_underscores(self):
        """Collapses multiple underscores."""
        assert sanitize_metric_name("my___metric") == "my_metric"

    def test_strip_underscores(self):
        """Strips leading and trailing underscores."""
        assert sanitize_metric_name("_my_metric_") == "my_metric"

    def test_empty_becomes_unnamed(self):
        """Empty string becomes 'unnamed'."""
        assert sanitize_metric_name("") == "unnamed"
        assert sanitize_metric_name("___") == "unnamed"

    def test_preserves_numbers(self):
        """Preserves numbers in names."""
        assert sanitize_metric_name("metric_v2_test") == "metric_v2_test"


class TestBuildGoalMetrics:
    """Test goal metric building."""

    def test_empty_goals(self):
        """Empty goal list returns empty dict."""
        assert build_goal_metrics([]) == {}

    def test_single_goal(self):
        """Single goal creates single metric."""
        goal = MagicMock()
        goal.name = "acknowledged_request"
        goal.score = 1.0

        result = build_goal_metrics([goal])
        assert result == {"goal_acknowledged_request": 1.0}

    def test_multiple_goals(self):
        """Multiple goals create multiple metrics."""
        goal1 = MagicMock()
        goal1.name = "goal_one"
        goal1.score = 0.8

        goal2 = MagicMock()
        goal2.name = "goal_two"
        goal2.score = 0.5

        result = build_goal_metrics([goal1, goal2])
        assert result == {
            "goal_goal_one": 0.8,
            "goal_goal_two": 0.5,
        }

    def test_sanitizes_goal_names(self):
        """Goal names are sanitized."""
        goal = MagicMock()
        goal.name = "My Goal Name"
        goal.score = 1.0

        result = build_goal_metrics([goal])
        assert "goal_my_goal_name" in result


class TestBuildTimingMetrics:
    """Test timing metric building."""

    def test_builds_total_ms(self):
        """Builds timing_total_ms metric."""
        result = build_timing_metrics(1234)
        assert result == {"timing_total_ms": 1234.0}

    def test_converts_to_float(self):
        """Converts int to float."""
        result = build_timing_metrics(100)
        assert isinstance(result["timing_total_ms"], float)


class TestBuildTokenMetrics:
    """Test token metric building."""

    def test_builds_all_token_metrics(self):
        """Builds input, output, and total token metrics."""
        result = build_token_metrics(100, 50)
        assert result == {
            "tokens_input": 100.0,
            "tokens_output": 50.0,
            "tokens_total": 150.0,
        }

    def test_handles_zero_tokens(self):
        """Handles zero token counts."""
        result = build_token_metrics(0, 0)
        assert result["tokens_total"] == 0.0


class TestBuildScoreMetrics:
    """Test score metric building."""

    def test_builds_all_score_metrics(self):
        """Builds total, max, and percentage metrics."""
        result = build_score_metrics(8.5, 10.0, 85.0)
        assert result == {
            "score_total": 8.5,
            "score_max": 10.0,
            "score_percentage": 85.0,
        }
