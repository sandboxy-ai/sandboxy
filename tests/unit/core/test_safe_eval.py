"""Tests for safe expression evaluation module."""

import pytest

from sandboxy.core.safe_eval import (
    SAFE_FUNCTIONS,
    EvaluationError,
    safe_eval,
    safe_eval_condition,
    safe_eval_formula,
)


class TestSafeEval:
    """Tests for safe_eval function."""

    # -------------------------------------------------------------------------
    # Basic Arithmetic
    # -------------------------------------------------------------------------

    def test_simple_addition(self) -> None:
        """Test basic addition."""
        assert safe_eval("1 + 2") == 3

    def test_simple_subtraction(self) -> None:
        """Test basic subtraction."""
        assert safe_eval("10 - 4") == 6

    def test_simple_multiplication(self) -> None:
        """Test basic multiplication."""
        assert safe_eval("5 * 6") == 30

    def test_simple_division(self) -> None:
        """Test basic division."""
        assert safe_eval("20 / 4") == 5.0

    def test_integer_division(self) -> None:
        """Test integer division."""
        assert safe_eval("17 // 5") == 3

    def test_modulo(self) -> None:
        """Test modulo operation."""
        assert safe_eval("17 % 5") == 2

    def test_exponentiation(self) -> None:
        """Test exponentiation."""
        assert safe_eval("2 ** 10") == 1024

    def test_complex_expression(self) -> None:
        """Test complex arithmetic expression."""
        assert safe_eval("(2 + 3) * 4 - 10 / 2") == 15.0

    # -------------------------------------------------------------------------
    # Comparison Operators
    # -------------------------------------------------------------------------

    def test_greater_than(self) -> None:
        """Test greater than comparison."""
        assert safe_eval("5 > 3") is True
        assert safe_eval("3 > 5") is False

    def test_less_than(self) -> None:
        """Test less than comparison."""
        assert safe_eval("3 < 5") is True
        assert safe_eval("5 < 3") is False

    def test_greater_than_or_equal(self) -> None:
        """Test greater than or equal comparison."""
        assert safe_eval("5 >= 5") is True
        assert safe_eval("6 >= 5") is True
        assert safe_eval("4 >= 5") is False

    def test_less_than_or_equal(self) -> None:
        """Test less than or equal comparison."""
        assert safe_eval("5 <= 5") is True
        assert safe_eval("4 <= 5") is True
        assert safe_eval("6 <= 5") is False

    def test_equality(self) -> None:
        """Test equality comparison."""
        assert safe_eval("5 == 5") is True
        assert safe_eval("5 == 6") is False
        assert safe_eval("'hello' == 'hello'") is True

    def test_inequality(self) -> None:
        """Test inequality comparison."""
        assert safe_eval("5 != 6") is True
        assert safe_eval("5 != 5") is False

    # -------------------------------------------------------------------------
    # Boolean Operations
    # -------------------------------------------------------------------------

    def test_boolean_and(self) -> None:
        """Test boolean AND."""
        assert safe_eval("True and True") is True
        assert safe_eval("True and False") is False
        assert safe_eval("False and True") is False
        assert safe_eval("False and False") is False

    def test_boolean_or(self) -> None:
        """Test boolean OR."""
        assert safe_eval("True or True") is True
        assert safe_eval("True or False") is True
        assert safe_eval("False or True") is True
        assert safe_eval("False or False") is False

    def test_boolean_not(self) -> None:
        """Test boolean NOT."""
        assert safe_eval("not True") is False
        assert safe_eval("not False") is True

    def test_complex_boolean(self) -> None:
        """Test complex boolean expression."""
        assert safe_eval("(True and False) or (not False)") is True

    # -------------------------------------------------------------------------
    # Context Variables
    # -------------------------------------------------------------------------

    def test_single_variable(self) -> None:
        """Test expression with single variable."""
        assert safe_eval("x + 5", {"x": 10}) == 15

    def test_multiple_variables(self) -> None:
        """Test expression with multiple variables."""
        context = {"a": 10, "b": 20, "c": 5}
        assert safe_eval("a + b - c", context) == 25

    def test_variable_comparison(self) -> None:
        """Test comparison with variables."""
        assert safe_eval("x > y", {"x": 10, "y": 5}) is True
        assert safe_eval("x > y", {"x": 5, "y": 10}) is False

    def test_nested_dict_access(self) -> None:
        """Test accessing nested dictionary values."""
        context = {"data": {"name": "test", "value": 42}}
        assert safe_eval("data['name']", context) == "test"
        assert safe_eval("data['value']", context) == 42

    def test_dict_get_method(self) -> None:
        """Test dict.get() method."""
        context = {"data": {"name": "test"}}
        assert safe_eval("data.get('name')", context) == "test"
        assert safe_eval("data.get('missing', 'default')", context) == "default"

    # -------------------------------------------------------------------------
    # Constants from SAFE_FUNCTIONS
    # -------------------------------------------------------------------------

    def test_true_false_none_constants(self) -> None:
        """Test True, False, None constants are available."""
        assert safe_eval("True") is True
        assert safe_eval("False") is False
        assert safe_eval("None") is None

    def test_constants_in_expressions(self) -> None:
        """Test constants work in expressions."""
        assert safe_eval("True and True") is True
        assert safe_eval("True or False") is True
        assert safe_eval("None == None") is True

    # -------------------------------------------------------------------------
    # List Operations
    # -------------------------------------------------------------------------

    def test_list_indexing(self) -> None:
        """Test list indexing."""
        context = {"items": [10, 20, 30, 40, 50]}
        assert safe_eval("items[0]", context) == 10
        assert safe_eval("items[-1]", context) == 50
        assert safe_eval("items[2]", context) == 30

    def test_list_slicing(self) -> None:
        """Test list slicing."""
        context = {"items": [1, 2, 3, 4, 5]}
        assert safe_eval("items[1:3]", context) == [2, 3]
        assert safe_eval("items[:2]", context) == [1, 2]
        assert safe_eval("items[3:]", context) == [4, 5]

    def test_list_in_operator(self) -> None:
        """Test 'in' operator with lists."""
        context = {"items": [1, 2, 3]}
        assert safe_eval("2 in items", context) is True
        assert safe_eval("5 in items", context) is False

    # -------------------------------------------------------------------------
    # String Operations
    # -------------------------------------------------------------------------

    def test_string_concatenation(self) -> None:
        """Test string concatenation."""
        assert safe_eval("'hello' + ' ' + 'world'") == "hello world"

    def test_string_in_operator(self) -> None:
        """Test 'in' operator with strings."""
        assert safe_eval("'ell' in 'hello'") is True
        assert safe_eval("'xyz' in 'hello'") is False

    def test_string_indexing(self) -> None:
        """Test string indexing."""
        context = {"text": "hello"}
        assert safe_eval("text[0]", context) == "h"
        assert safe_eval("text[-1]", context) == "o"

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_empty_expression_raises_error(self) -> None:
        """Test that empty expressions raise EvaluationError."""
        with pytest.raises(EvaluationError, match="Empty expression"):
            safe_eval("")

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only expressions raise EvaluationError."""
        with pytest.raises(EvaluationError, match="Empty expression"):
            safe_eval("   ")

    def test_undefined_variable_raises_error(self) -> None:
        """Test that undefined variables raise EvaluationError."""
        with pytest.raises(EvaluationError):
            safe_eval("undefined_variable + 1")

    def test_invalid_syntax_raises_error(self) -> None:
        """Test that invalid syntax raises EvaluationError."""
        with pytest.raises(EvaluationError):
            safe_eval("1 +* 2")  # Invalid operator sequence

    def test_division_by_zero_raises_error(self) -> None:
        """Test that division by zero raises EvaluationError."""
        with pytest.raises(EvaluationError):
            safe_eval("1 / 0")


class TestSafeEvalCondition:
    """Tests for safe_eval_condition function."""

    def test_true_condition(self) -> None:
        """Test condition that evaluates to True."""
        assert safe_eval_condition("5 > 3") is True

    def test_false_condition(self) -> None:
        """Test condition that evaluates to False."""
        assert safe_eval_condition("5 < 3") is False

    def test_condition_with_variables(self) -> None:
        """Test condition with variables."""
        assert safe_eval_condition("x > 10", {"x": 15}) is True
        assert safe_eval_condition("x > 10", {"x": 5}) is False

    def test_empty_condition_returns_false(self) -> None:
        """Test that empty condition returns False."""
        assert safe_eval_condition("") is False
        assert safe_eval_condition("   ") is False

    def test_invalid_condition_returns_false(self) -> None:
        """Test that invalid conditions return False instead of raising."""
        # Undefined variable - should return False, not raise
        assert safe_eval_condition("undefined_var") is False

    def test_non_boolean_result_coerced(self) -> None:
        """Test that non-boolean results are coerced to bool."""
        assert safe_eval_condition("1") is True
        assert safe_eval_condition("0") is False
        assert safe_eval_condition("'non-empty'") is True
        assert safe_eval_condition("''") is False

    def test_complex_condition(self) -> None:
        """Test complex boolean condition."""
        context = {"a": 10, "b": 5, "c": True}
        assert safe_eval_condition("a > b and c", context) is True
        assert safe_eval_condition("a < b or c", context) is True


class TestSafeEvalFormula:
    """Tests for safe_eval_formula function."""

    def test_simple_formula(self) -> None:
        """Test simple score formula."""
        check_values = {"score": 50.0}
        assert safe_eval_formula("score", check_values) == 50.0

    def test_arithmetic_formula(self) -> None:
        """Test formula with arithmetic operations."""
        check_values = {"a": 10.0, "b": 5.0}
        assert safe_eval_formula("a + b", check_values) == 15.0
        assert safe_eval_formula("a * b", check_values) == 50.0

    def test_weighted_formula(self) -> None:
        """Test weighted score formula."""
        check_values = {"quality": 0.8, "speed": 0.6}
        result = safe_eval_formula("quality * 2 + speed * 1", check_values)
        assert result == pytest.approx(2.2)

    def test_formula_with_list_access(self) -> None:
        """Test formula accessing list elements."""
        check_values = {"score1": 70.0, "score2": 80.0, "score3": 90.0}
        result = safe_eval_formula("(score1 + score2 + score3) / 3", check_values)
        assert result == 80.0

    def test_formula_with_env_state(self) -> None:
        """Test formula with environment state access."""
        check_values = {"base_score": 50.0}
        env_state = {"bonus": 10.0, "penalty": 5.0}
        result = safe_eval_formula(
            "base_score + env_state['bonus'] - env_state['penalty']",
            check_values,
            env_state,
        )
        assert result == 55.0

    def test_formula_must_return_number(self) -> None:
        """Test that non-numeric results raise EvaluationError."""
        with pytest.raises(EvaluationError, match="must return a number"):
            safe_eval_formula("'not a number'", {})

    def test_formula_with_boolean_check(self) -> None:
        """Test formula where check values are booleans (converted to 0/1)."""
        check_values = {"passed": 1.0, "failed": 0.0}
        assert safe_eval_formula("passed + failed", check_values) == 1.0

    def test_complex_formula(self) -> None:
        """Test a complex scoring formula."""
        check_values = {
            "profit": 100.0,
            "customers_served": 5.0,
            "customers_lost": 1.0,
        }
        formula = "profit + customers_served * 10 - customers_lost * 20"
        result = safe_eval_formula(formula, check_values)
        assert result == 130.0  # 100 + 50 - 20


class TestSafeFunctions:
    """Tests for SAFE_FUNCTIONS constant."""

    def test_safe_functions_includes_constants(self) -> None:
        """Test that SAFE_FUNCTIONS includes boolean/None constants."""
        assert "True" in SAFE_FUNCTIONS
        assert "False" in SAFE_FUNCTIONS
        assert "None" in SAFE_FUNCTIONS

    def test_safe_functions_includes_type_functions(self) -> None:
        """Test that SAFE_FUNCTIONS defines type conversion functions."""
        # These are defined in SAFE_FUNCTIONS (though may not be callable as functions)
        expected = ["str", "int", "float", "bool", "list", "dict"]
        for func_name in expected:
            assert func_name in SAFE_FUNCTIONS

    def test_safe_functions_excludes_dangerous(self) -> None:
        """Test that SAFE_FUNCTIONS excludes dangerous functions."""
        dangerous = ["eval", "exec", "compile", "open", "__import__", "globals", "locals"]
        for func_name in dangerous:
            assert func_name not in SAFE_FUNCTIONS
