"""Tests for MDL parser module."""

from pathlib import Path

import pytest

from sandboxy.core.mdl_parser import (
    MDLParseError,
    apply_variables,
    interpolate_template,
    load_module,
    parse_module,
    validate_module,
)


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
        assert len(module.evaluation) == 0

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
                        "type": "mock_shopify",
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
        assert module.environment.tools[0].config == {"key": "value"}
        assert module.environment.initial_state["cash"] == 100.0
        assert len(module.steps) == 2
        assert module.steps[0].action == "inject_user"
        assert len(module.branches) == 1
        assert len(module.branches["refund_path"]) == 1
        assert len(module.evaluation) == 1

    def test_parse_missing_id_raises_error(self) -> None:
        """Test that missing id raises MDLParseError."""
        raw = {"environment": {}}
        with pytest.raises(MDLParseError, match="must have an 'id' field"):
            parse_module(raw)

    def test_parse_module_with_variables(self) -> None:
        """Test parsing module with variable definitions."""
        raw = {
            "id": "test/vars",
            "variables": [
                {
                    "name": "difficulty",
                    "label": "Difficulty Level",
                    "type": "select",
                    "default": "easy",
                    "options": [
                        {"value": "easy", "label": "Easy"},
                        {"value": "hard", "label": "Hard"},
                    ],
                },
                {
                    "name": "budget",
                    "label": "Starting Budget",
                    "type": "slider",
                    "default": 100,
                    "min": 0,
                    "max": 1000,
                    "step": 10,
                },
            ],
            "environment": {},
            "steps": [],
        }
        module = parse_module(raw)

        assert len(module.variables) == 2
        assert module.variables[0].name == "difficulty"
        assert module.variables[0].type == "select"
        assert len(module.variables[0].options) == 2
        assert module.variables[1].name == "budget"
        assert module.variables[1].min == 0
        assert module.variables[1].max == 1000

    def test_parse_evaluation_checks(self) -> None:
        """Test parsing various evaluation check types."""
        raw = {
            "id": "test/checks",
            "environment": {},
            "steps": [],
            "evaluation": [
                {
                    "name": "ContainsCheck",
                    "kind": "contains",
                    "target": "agent_messages",
                    "value": "hello",
                    "expected": True,
                    "case_sensitive": False,
                },
                {
                    "name": "ToolCheck",
                    "kind": "tool_called",
                    "tool": "shopify",
                    "action": "refund_order",
                    "expected": True,
                },
                {
                    "name": "EnvCheck",
                    "kind": "env_state",
                    "key": "balance",
                    "value": 100,
                },
            ],
        }
        module = parse_module(raw)

        assert len(module.evaluation) == 3
        assert module.evaluation[0].kind == "contains"
        assert module.evaluation[0].case_sensitive is False
        assert module.evaluation[1].kind == "tool_called"
        assert module.evaluation[1].tool == "shopify"
        assert module.evaluation[2].kind == "env_state"
        assert module.evaluation[2].key == "balance"

    def test_parse_scoring_config(self) -> None:
        """Test parsing scoring configuration."""
        raw = {
            "id": "test/scoring",
            "environment": {},
            "steps": [],
            "scoring": {
                "formula": "check1 * 2 + check2",
                "weights": {"check1": 2.0, "check2": 1.0},
                "normalize": True,
                "min_score": 0.0,
                "max_score": 100.0,
            },
        }
        module = parse_module(raw)

        assert module.scoring.formula == "check1 * 2 + check2"
        assert module.scoring.weights == {"check1": 2.0, "check2": 1.0}
        assert module.scoring.normalize is True
        assert module.scoring.min_score == 0.0
        assert module.scoring.max_score == 100.0

    def test_parse_agent_config(self) -> None:
        """Test parsing agent configuration."""
        raw = {
            "id": "test/agent",
            "agent_config": {
                "system_prompt": "You are a helpful assistant.",
                "temperature": 0.7,
            },
            "environment": {},
            "steps": [],
        }
        module = parse_module(raw)

        assert module.agent_config["system_prompt"] == "You are a helpful assistant."
        assert module.agent_config["temperature"] == 0.7

    def test_parse_step_with_condition(self) -> None:
        """Test parsing steps with conditions."""
        raw = {
            "id": "test/conditional",
            "environment": {},
            "steps": [
                {
                    "id": "s1",
                    "action": "inject_user",
                    "params": {"content": "Hello"},
                    "condition": "difficulty == 'hard'",
                },
            ],
        }
        module = parse_module(raw)

        assert module.steps[0].condition == "difficulty == 'hard'"


class TestLoadModule:
    """Tests for load_module function."""

    def test_load_valid_yaml(self, temp_yaml_file) -> None:
        """Test loading a valid YAML file."""
        temp_dir, create_yaml = temp_yaml_file
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
        path = create_yaml(yaml_content)
        module = load_module(path)

        assert module.id == "test/yaml-load"
        assert len(module.steps) == 1

    def test_load_invalid_yaml_raises_error(self, temp_yaml_file) -> None:
        """Test loading invalid YAML raises MDLParseError."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = "invalid: yaml: content: [unbalanced"
        path = create_yaml(yaml_content)

        with pytest.raises(MDLParseError, match="Invalid YAML"):
            load_module(path)

    def test_load_nonexistent_file_raises_error(self) -> None:
        """Test loading nonexistent file raises MDLParseError."""
        with pytest.raises(MDLParseError, match="File not found"):
            load_module(Path("/nonexistent/path/module.yml"))

    def test_load_non_dict_yaml_raises_error(self, temp_yaml_file) -> None:
        """Test loading YAML that isn't a dict raises error."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = "- list\n- of\n- items"
        path = create_yaml(yaml_content)

        with pytest.raises(MDLParseError, match="must be a YAML mapping"):
            load_module(path)


class TestValidateModule:
    """Tests for validate_module function."""

    def test_validate_valid_module(self, temp_yaml_file) -> None:
        """Test validation of a valid module."""
        temp_dir, create_yaml = temp_yaml_file
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
        path = create_yaml(yaml_content)
        errors = validate_module(path)

        assert len(errors) == 0

    def test_validate_invalid_action(self, temp_yaml_file) -> None:
        """Test validation catches invalid action."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = """
id: test/invalid-action
environment: {}
steps:
  - id: s1
    action: invalid_action
    params: {}
"""
        path = create_yaml(yaml_content)
        errors = validate_module(path)

        assert len(errors) == 1
        assert "invalid action" in errors[0].lower()

    def test_validate_invalid_branch_reference(self, temp_yaml_file) -> None:
        """Test validation catches invalid branch reference."""
        temp_dir, create_yaml = temp_yaml_file
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
        path = create_yaml(yaml_content)
        errors = validate_module(path)

        assert len(errors) == 1
        assert "unknown branch" in errors[0].lower()

    def test_validate_invalid_eval_kind(self, temp_yaml_file) -> None:
        """Test validation catches invalid evaluation kind."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = """
id: test/invalid-eval
environment: {}
steps: []
evaluation:
  - name: check1
    kind: invalid_kind
    config: {}
"""
        path = create_yaml(yaml_content)
        errors = validate_module(path)

        assert len(errors) == 1
        assert "invalid kind" in errors[0].lower()

    def test_validate_multiple_errors(self, temp_yaml_file) -> None:
        """Test validation catches multiple errors."""
        temp_dir, create_yaml = temp_yaml_file
        yaml_content = """
id: test/multiple-errors
environment: {}
steps:
  - id: s1
    action: bad_action
    params: {}
  - id: s2
    action: another_bad
    params: {}
"""
        path = create_yaml(yaml_content)
        errors = validate_module(path)

        assert len(errors) == 2


class TestInterpolateTemplate:
    """Tests for interpolate_template function."""

    def test_simple_variable_substitution(self) -> None:
        """Test simple variable substitution."""
        result = interpolate_template("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_multiple_variables(self) -> None:
        """Test multiple variable substitutions."""
        result = interpolate_template(
            "{{greeting}} {{name}}!",
            {"greeting": "Hi", "name": "Alice"},
        )
        assert result == "Hi Alice!"

    def test_missing_variable_unchanged(self) -> None:
        """Test that missing variables are left unchanged."""
        result = interpolate_template("Hello {{name}}", {})
        assert "{{" in result  # Variable placeholder preserved

    def test_if_block_true(self) -> None:
        """Test if block when condition is true."""
        result = interpolate_template(
            "{{#if show}}Visible{{/if}}",
            {"show": True},
        )
        assert result == "Visible"

    def test_if_block_false(self) -> None:
        """Test if block when condition is false."""
        result = interpolate_template(
            "{{#if show}}Visible{{/if}}",
            {"show": False},
        )
        assert result == ""

    def test_if_else_block(self) -> None:
        """Test if-else block."""
        template = "{{#if premium}}Premium user{{else}}Free user{{/if}}"

        assert interpolate_template(template, {"premium": True}) == "Premium user"
        assert interpolate_template(template, {"premium": False}) == "Free user"

    def test_if_else_if_block(self) -> None:
        """Test if-else-if-else chain."""
        template = (
            """{{#if level == 'high'}}High{{else if level == 'medium'}}Medium{{else}}Low{{/if}}"""
        )

        assert interpolate_template(template, {"level": "high"}) == "High"
        assert interpolate_template(template, {"level": "medium"}) == "Medium"
        assert interpolate_template(template, {"level": "low"}) == "Low"

    def test_numeric_comparison(self) -> None:
        """Test numeric comparison in condition."""
        template = "{{#if score >= 70}}Pass{{else}}Fail{{/if}}"

        assert interpolate_template(template, {"score": 85}) == "Pass"
        assert interpolate_template(template, {"score": 50}) == "Fail"

    def test_empty_template(self) -> None:
        """Test empty template returns empty string."""
        assert interpolate_template("", {}) == ""
        assert interpolate_template(None, {}) is None


class TestApplyVariables:
    """Tests for apply_variables function."""

    def test_apply_to_system_prompt(self) -> None:
        """Test variables are applied to system prompt."""
        raw = {
            "id": "test/prompt",
            "agent_config": {
                "system_prompt": "You are helping {{customer_name}}.",
            },
            "environment": {},
            "steps": [],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"customer_name": "Alice"})

        assert result.agent_config["system_prompt"] == "You are helping Alice."

    def test_apply_to_initial_state(self) -> None:
        """Test variables are applied to initial state."""
        raw = {
            "id": "test/state",
            "environment": {
                "initial_state": {
                    "balance": "{{starting_balance}}",
                },
            },
            "steps": [],
            "variables": [
                {"name": "starting_balance", "label": "Balance", "default": 100},
            ],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"starting_balance": 500})

        assert result.environment.initial_state["balance"] == 500

    def test_apply_to_step_params(self) -> None:
        """Test variables are applied to step params."""
        raw = {
            "id": "test/steps",
            "environment": {},
            "steps": [
                {
                    "id": "s1",
                    "action": "inject_user",
                    "params": {"content": "Hello {{name}}"},
                },
            ],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"name": "Bob"})

        assert result.steps[0].params["content"] == "Hello Bob"

    def test_conditional_step_included(self) -> None:
        """Test step with true condition is included."""
        raw = {
            "id": "test/conditional",
            "environment": {},
            "steps": [
                {
                    "id": "s1",
                    "action": "inject_user",
                    "params": {"content": "Hard mode"},
                    "condition": "difficulty == 'hard'",
                },
            ],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"difficulty": "hard"})

        assert len(result.steps) == 1
        assert result.steps[0].params["content"] == "Hard mode"

    def test_conditional_step_excluded(self) -> None:
        """Test step with false condition is excluded."""
        raw = {
            "id": "test/conditional",
            "environment": {},
            "steps": [
                {
                    "id": "s1",
                    "action": "inject_user",
                    "params": {"content": "Hard mode"},
                    "condition": "difficulty == 'hard'",
                },
            ],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"difficulty": "easy"})

        assert len(result.steps) == 0

    def test_uses_default_values(self) -> None:
        """Test that default variable values are used."""
        raw = {
            "id": "test/defaults",
            "variables": [
                {"name": "greeting", "label": "Greeting", "default": "Hello"},
            ],
            "agent_config": {
                "system_prompt": "{{greeting}} there!",
            },
            "environment": {},
            "steps": [],
        }
        module = parse_module(raw)
        result = apply_variables(module, {})  # No overrides

        assert result.agent_config["system_prompt"] == "Hello there!"

    def test_apply_to_tool_config(self) -> None:
        """Test variables are applied to tool configuration."""
        raw = {
            "id": "test/tools",
            "environment": {
                "tools": [
                    {
                        "name": "store",
                        "type": "mock_store",
                        "config": {
                            "inventory": "{{initial_inventory}}",
                        },
                    },
                ],
            },
            "steps": [],
        }
        module = parse_module(raw)
        result = apply_variables(module, {"initial_inventory": 50})

        assert result.environment.tools[0].config["inventory"] == 50
