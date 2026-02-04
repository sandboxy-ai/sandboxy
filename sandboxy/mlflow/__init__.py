"""MLflow integration for Sandboxy scenario tracking and evaluation."""

from sandboxy.mlflow.config import MLflowConfig

__all__ = [
    "MLflowConfig",
    "MLflowExporter",
    "mlflow_run_context",
    "enable_tracing",
    "disable_tracing",
    "trace_span",
]


def __getattr__(name: str):
    """Lazy import to avoid mlflow import when not needed."""
    if name == "MLflowExporter":
        from sandboxy.mlflow.exporter import MLflowExporter

        return MLflowExporter
    if name == "mlflow_run_context":
        from sandboxy.mlflow.exporter import mlflow_run_context

        return mlflow_run_context
    if name == "enable_tracing":
        from sandboxy.mlflow.tracing import enable_tracing

        return enable_tracing
    if name == "disable_tracing":
        from sandboxy.mlflow.tracing import disable_tracing

        return disable_tracing
    if name == "trace_span":
        from sandboxy.mlflow.tracing import trace_span

        return trace_span
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
