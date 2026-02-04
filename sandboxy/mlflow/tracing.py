"""MLflow tracing support for Sandboxy.

Enables automatic tracing of LLM calls using MLflow's autolog feature.
When enabled, all OpenAI SDK calls are automatically captured as spans
within the MLflow run, providing detailed visibility into:
- Each LLM call (prompt, response, latency, tokens)
- Tool/function calls made by the LLM
- The full execution flow
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_tracing_enabled = False


def enable_tracing(
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
) -> bool:
    """Enable MLflow tracing for OpenAI calls.

    This should be called once before any LLM calls are made.
    It enables MLflow's autolog feature which automatically
    captures all OpenAI SDK calls as traces.

    Args:
        tracking_uri: MLflow tracking server URI (uses env var if not set)
        experiment_name: Experiment to log traces to

    Returns:
        True if tracing was enabled successfully, False otherwise
    """
    global _tracing_enabled

    if _tracing_enabled:
        return True

    try:
        import os

        import mlflow

        # Set tracking URI before enabling autolog
        uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI")
        if uri:
            mlflow.set_tracking_uri(uri)

        # Set experiment before enabling autolog
        if experiment_name:
            mlflow.set_experiment(experiment_name)

        # Enable OpenAI autologging - this captures all OpenAI calls as traces
        mlflow.openai.autolog()

        _tracing_enabled = True
        logger.debug("MLflow tracing enabled for OpenAI")
        return True

    except ImportError as e:
        logger.warning(f"MLflow or OpenAI not installed, tracing disabled: {e}")
        return False
    except Exception as e:
        logger.warning(f"Failed to enable MLflow tracing: {e}")
        return False


def disable_tracing() -> None:
    """Disable MLflow tracing."""
    global _tracing_enabled

    if not _tracing_enabled:
        return

    try:
        import mlflow

        mlflow.openai.autolog(disable=True)
        _tracing_enabled = False
        logger.debug("MLflow tracing disabled")

    except Exception as e:
        logger.warning(f"Failed to disable MLflow tracing: {e}")


@contextmanager
def trace_span(name: str, span_type: str = "CHAIN") -> Generator[None, None, None]:
    """Create a manual trace span for non-LLM operations.

    Use this to wrap tool calls, scenario steps, or other operations
    you want to appear in the trace.

    Args:
        name: Name of the span (e.g., "tool_call:get_account_activity")
        span_type: Type of span (CHAIN, TOOL, RETRIEVER, etc.)

    Example:
        with trace_span("tool_call:search", span_type="TOOL"):
            result = execute_tool(...)
    """
    try:
        import mlflow

        with mlflow.start_span(name=name, span_type=span_type):
            yield

    except ImportError:
        # MLflow not installed, just run without tracing
        yield
    except Exception as e:
        logger.debug(f"Tracing span failed: {e}")
        yield


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled."""
    return _tracing_enabled
