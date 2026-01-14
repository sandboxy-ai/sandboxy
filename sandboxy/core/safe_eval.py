"""Safe expression evaluation module.

Provides sandboxed expression evaluation using simpleeval, replacing raw eval()
calls throughout the codebase with a secure, consistent implementation.

Security features:
- Only whitelisted functions/operators are allowed
- No access to __builtins__, __import__, or dunder methods
- Consistent evaluation context across all callers
- Proper error handling with typed exceptions
"""

import logging
from typing import Any

from simpleeval import EvalWithCompoundTypes, InvalidExpression

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Error during expression evaluation."""

    def __init__(self, message: str, expression: str | None = None) -> None:
        """Initialize evaluation error with message and optional expression.

        Args:
            message: Error message describing what went wrong.
            expression: The expression that caused the error, if applicable.
        """
        super().__init__(message)
        self.expression = expression


# Safe functions available in all evaluations
SAFE_FUNCTIONS = {
    # Type conversions
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    # Math
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    # Collections
    "len": len,
    "any": any,
    "all": all,
    "sorted": sorted,
    "reversed": lambda x: list(reversed(x)),
    # Constants
    "True": True,
    "False": False,
    "None": None,
}


def safe_eval(
    expr: str,
    context: dict[str, Any] | None = None,
) -> Any:
    """Safely evaluate an expression with restricted scope.

    Uses simpleeval to provide a sandboxed evaluation environment.
    Only whitelisted functions are available.

    Args:
        expr: Expression to evaluate.
        context: Additional variables available in the expression.

    Returns:
        Result of the expression evaluation.

    Raises:
        EvaluationError: If the expression is invalid or evaluation fails.

    """
    if not expr or not expr.strip():
        raise EvaluationError("Empty expression", expr)

    # Build evaluation context
    names = dict(SAFE_FUNCTIONS)
    if context:
        names.update(context)

    try:
        evaluator = EvalWithCompoundTypes(names=names)
        return evaluator.eval(expr)
    except InvalidExpression as e:
        logger.debug("Invalid expression '%s': %s", expr, e)
        msg = f"Invalid expression: {e}"
        raise EvaluationError(msg, expr) from e
    except (TypeError, ValueError, KeyError, AttributeError) as e:
        logger.debug("Evaluation error for '%s': %s", expr, e)
        msg = f"Evaluation failed: {e}"
        raise EvaluationError(msg, expr) from e
    except Exception as e:
        # Catch any other errors from simpleeval
        logger.warning("Unexpected evaluation error for '%s': %s", expr, e)
        msg = f"Evaluation failed: {e}"
        raise EvaluationError(msg, expr) from e


def safe_eval_condition(
    condition: str,
    variables: dict[str, Any] | None = None,
) -> bool:
    """Safely evaluate a boolean condition.

    Args:
        condition: Condition expression (e.g., "x > 5", "name == 'test'").
        variables: Variables available in the condition.

    Returns:
        Boolean result of the condition.

    Note:
        Returns False if evaluation fails (defensive default for conditions).

    """
    if not condition or not condition.strip():
        return False

    try:
        result = safe_eval(condition, variables)
        return bool(result)
    except EvaluationError:
        return False


def safe_eval_formula(
    formula: str,
    check_values: dict[str, float],
    env_state: dict[str, Any] | None = None,
) -> float:
    """Safely evaluate a score formula.

    Args:
        formula: Formula expression (e.g., "score * 0.5 + bonus").
        check_values: Check result values available as variables.
        env_state: Optional environment state for advanced formulas.

    Returns:
        Numeric result of the formula.

    Raises:
        EvaluationError: If the formula is invalid or doesn't return a number.

    """
    context = dict(check_values)
    if env_state:
        context["env_state"] = env_state

    result = safe_eval(formula, context)

    try:
        return float(result)
    except (TypeError, ValueError) as e:
        msg = f"Formula must return a number, got {type(result).__name__}"
        raise EvaluationError(msg, formula) from e
