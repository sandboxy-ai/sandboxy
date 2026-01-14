"""Base provider interface and common types."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    """Error from an LLM provider."""

    def __init__(self, message: str, provider: str, model: str | None = None):
        """Initialize provider error.

        Args:
            message: Error description
            provider: Provider name that raised the error
            model: Model ID if applicable

        """
        self.provider = provider
        self.model = model
        super().__init__(f"[{provider}] {message}")


@dataclass
class ModelResponse:
    """Response from a model completion."""

    content: str
    model_id: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = field(default=None, repr=False)


@dataclass
class ModelInfo:
    """Information about an available model."""

    id: str
    name: str
    provider: str
    context_length: int
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a completion request to the model.

        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-3-opus")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific options

        Returns:
            ModelResponse with content and metadata

        Raises:
            ProviderError: If the request fails

        """
        pass

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a completion response.

        Default implementation falls back to non-streaming.
        Override in subclasses for true streaming support.
        """
        response = await self.complete(model, messages, temperature, max_tokens, **kwargs)
        yield response.content

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """List available models from this provider.

        Returns:
            List of ModelInfo objects

        """
        pass

    def supports_model(self, model_id: str) -> bool:
        """Check if this provider supports a given model.

        Args:
            model_id: Model identifier to check

        Returns:
            True if the model is supported

        """
        return any(m.id == model_id for m in self.list_models())
