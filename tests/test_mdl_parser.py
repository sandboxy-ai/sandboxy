"""Tests for MDL parser."""

import tempfile
from pathlib import Path

import pytest

from sandboxy.core.mdl_parser import MDLParseError, load_module, parse_module, validate_module


class TestParseModule:
    """Tests for parse_module function."""

    def test_parse_minimal_module(self) -> None:
        """Test parsing a minimal valid module."""
        raw = {
            "id": "test/minimal",
            "environment": {},
            "steps": [],
        }
        module = parse_module(raw)
        assert module.id == "test/minimal"
        assert module.description == ""
        assert len(module.steps) == 0

    def test_parse_full_module(self) -> None:
        """Test parsing a complete module with all fields."""
        raw = {
            "id": "test/full",
            "description": "A full test module",
            "environment": {
                "sandbox_type": "local",
                "tools": [
                    {
                        "name": "shopify",
                        "type": "fake_shopify",
                        "description": "Mock store",
                        "config": {"key": "value"},
                    }
                ],
                "initial_state": {"cash": 100.0},
            },
            "steps": [
                {"id": "s1", "action": "inject_user", "params": {"content": "Hello"}},
                {"id": "s2", "action": "await_agent", "params": {}},
            ],
            "branches": {
                "refund_path": [
                    {"id": "b1", "action": "inject_user", "params": {"content": "Refund please"}},
                ]
            },
            "evaluation": [
                {"name": "check1", "kind": "deterministic", "config": {"expr": "True"}},
            ],
        }
        module = parse_module(raw)

        assert module.id == "test/full"
        assert module.description == "A full test module"
        assert module.environment.sandbox_type == "local"
        assert len(module.environment.tools) == 1
        assert module.environment.tools[0].name == "shopify"
        assert module.environment.initial_state["cash"] == 100.0
        assert len(module.steps) == 2
        assert module.steps[0].action == "inject_user"
        assert len(module.branches) == 1
        assert len(module.branches["refund_path"]) == 1
        assert len(module.evaluation) == 1

    def test_parse_missing_id(self) -> None:
        """Test that missing id raises error."""
        raw = {"environment": {}}
        with pytest.raises(MDLParseError, match="must have an 'id' field"):
            parse_module(raw)


class TestLoadModule:
    """Tests for load_module function."""

    def test_load_valid_yaml(self) -> None:
        """Test loading a valid YAML file."""
        yaml_content = """
id: test/yaml-load
description: Test module
environment:
  sandbox_type: local
  tools: []
steps:
  - id: s1
    action: inject_user
    params:
      content: Hello
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            module = load_module(path)
            assert module.id == "test/yaml-load"
            assert len(module.steps) == 1
        finally:
            path.unlink()

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises error."""
        yaml_content = "invalid: yaml: content: [unbalanced"
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            with pytest.raises(MDLParseError, match="Invalid YAML"):
                load_module(path)
        finally:
            path.unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading nonexistent file raises error."""
        with pytest.raises(MDLParseError, match="File not found"):
            load_module(Path("/nonexistent/path/module.yml"))


class TestValidateModule:
    """Tests for validate_module function."""

    def test_validate_valid_module(self) -> None:
        """Test validation of a valid module."""
        yaml_content = """
id: test/valid
environment: {}
steps:
  - id: s1
    action: inject_user
    params: {}
  - id: s2
    action: await_agent
    params: {}
evaluation:
  - name: check1
    kind: deterministic
    config: {}
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            errors = validate_module(path)
            assert len(errors) == 0
        finally:
            path.unlink()

    def test_validate_invalid_action(self) -> None:
        """Test validation catches invalid action."""
        yaml_content = """
id: test/invalid-action
environment: {}
steps:
  - id: s1
    action: invalid_action
    params: {}
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            errors = validate_module(path)
            assert len(errors) == 1
            assert "invalid action" in errors[0]
        finally:
            path.unlink()

    def test_validate_invalid_branch_reference(self) -> None:
        """Test validation catches invalid branch reference."""
        yaml_content = """
id: test/invalid-branch
environment: {}
steps:
  - id: s1
    action: branch
    params:
      branch_name: nonexistent
branches: {}
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            errors = validate_module(path)
            assert len(errors) == 1
            assert "unknown branch" in errors[0]
        finally:
            path.unlink()

    def test_validate_invalid_eval_kind(self) -> None:
        """Test validation catches invalid evaluation kind."""
        yaml_content = """
id: test/invalid-eval
environment: {}
steps: []
evaluation:
  - name: check1
    kind: invalid_kind
    config: {}
"""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False, mode="w") as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            errors = validate_module(path)
            assert len(errors) == 1
            assert "invalid kind" in errors[0]
        finally:
            path.unlink()
