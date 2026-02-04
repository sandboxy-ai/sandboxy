"""Tests for MLflow tag helpers."""

from unittest.mock import MagicMock, patch

from sandboxy.mlflow.tags import (
    build_standard_tags,
    get_commit_hash,
    get_sandboxy_version,
    parse_model_provider,
)


class TestParseModelProvider:
    """Test model provider parsing."""

    def test_openai_provider(self):
        """Extracts openai from model string."""
        assert parse_model_provider("openai/gpt-4o") == "openai"

    def test_anthropic_provider(self):
        """Extracts anthropic from model string."""
        assert parse_model_provider("anthropic/claude-3.5-sonnet") == "anthropic"

    def test_google_provider(self):
        """Extracts google from model string."""
        assert parse_model_provider("google/gemini-2.0-flash") == "google"

    def test_no_provider(self):
        """Returns 'unknown' when no provider prefix."""
        assert parse_model_provider("gpt-4o") == "unknown"

    def test_multiple_slashes(self):
        """Only uses first slash as separator."""
        assert parse_model_provider("meta-llama/llama-3/70b") == "meta-llama"


class TestGetCommitHash:
    """Test git commit hash retrieval."""

    def test_returns_short_hash(self):
        """Returns 8-character short hash when in git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123def456789\n",
            )
            result = get_commit_hash()
            assert result == "abc123de"  # First 8 chars

    def test_returns_none_outside_git_repo(self):
        """Returns None when not in git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128)
            result = get_commit_hash()
            assert result is None

    def test_handles_subprocess_error(self):
        """Returns None on subprocess error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("git not found")
            result = get_commit_hash()
            assert result is None


class TestGetSandboxyVersion:
    """Test version retrieval."""

    def test_returns_version_string(self):
        """Returns a version string."""
        version = get_sandboxy_version()
        assert isinstance(version, str)
        assert version != ""


class TestBuildStandardTags:
    """Test standard tag building."""

    def create_mock_result(self, model="openai/gpt-4o", error=None):
        """Create a mock RunResult."""
        result = MagicMock()
        result.model = model
        result.error = error
        return result

    def test_includes_all_required_tags(self):
        """Includes all required standard tags."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test Scenario",
            scenario_id="test-scenario",
        )

        assert "sandboxy_version" in tags
        assert tags["scenario_name"] == "Test Scenario"
        assert tags["scenario_id"] == "test-scenario"
        assert tags["model_name"] == "openai/gpt-4o"
        assert tags["model_provider"] == "openai"
        assert tags["status"] == "success"
        assert tags["agent_name"] == "default"

    def test_status_failed_on_error(self):
        """Sets status to 'failed' when error present."""
        result = self.create_mock_result(error="Something went wrong")
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert tags["status"] == "failed"

    def test_custom_agent_name(self):
        """Uses custom agent name when provided."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
            agent_name="my-agent",
        )
        assert tags["agent_name"] == "my-agent"

    def test_includes_dataset_case(self):
        """Includes dataset_case when provided."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
            dataset_case="case-001",
        )
        assert tags["dataset_case"] == "case-001"

    def test_excludes_dataset_case_when_none(self):
        """Excludes dataset_case when not provided."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert "dataset_case" not in tags

    @patch("sandboxy.mlflow.tags.get_commit_hash")
    def test_includes_commit_hash_when_available(self, mock_get_hash):
        """Includes commit_hash when in git repo."""
        mock_get_hash.return_value = "abc12345"
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert tags["commit_hash"] == "abc12345"

    @patch("sandboxy.mlflow.tags.get_commit_hash")
    def test_excludes_commit_hash_when_not_available(self, mock_get_hash):
        """Excludes commit_hash when not in git repo."""
        mock_get_hash.return_value = None
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert "commit_hash" not in tags


class TestDatasetCaseTagging:
    """Test dataset_case tag support for multi-model comparison."""

    def create_mock_result(self, model="openai/gpt-4o"):
        """Create a mock RunResult."""
        result = MagicMock()
        result.model = model
        result.error = None
        return result

    def test_dataset_case_included_when_provided(self):
        """dataset_case tag is included when running dataset benchmarks."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
            dataset_case="case-001",
        )
        assert tags["dataset_case"] == "case-001"

    def test_dataset_case_excluded_when_not_provided(self):
        """dataset_case tag is excluded for single runs."""
        result = self.create_mock_result()
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert "dataset_case" not in tags

    def test_model_tags_for_comparison(self):
        """model_name and model_provider are set for comparison filtering."""
        result = self.create_mock_result(model="anthropic/claude-3")
        tags = build_standard_tags(
            result=result,
            scenario_name="Test",
            scenario_id="test",
        )
        assert tags["model_name"] == "anthropic/claude-3"
        assert tags["model_provider"] == "anthropic"
