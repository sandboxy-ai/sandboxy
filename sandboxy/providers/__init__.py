"""Multi-model provider abstraction layer.

Supports multiple LLM providers through a unified interface:
- OpenRouter (400+ models via single API)
- OpenAI (direct)
- Anthropic (direct)

Usage:
    from sandboxy.providers import get_provider, ProviderRegistry

    # Get provider for a specific model
    provider = get_provider("openai/gpt-4o")
    response = await provider.complete("openai/gpt-4o", messages)

    # Or use the registry
    registry = ProviderRegistry()
    provider = registry.get_provider_for_model("anthropic/claude-3-opus")
"""

from sandboxy.providers.base import (
    BaseProvider,
    ModelResponse,
    ProviderError,
)
from sandboxy.providers.registry import ProviderRegistry, get_provider, get_registry

__all__ = [
    "BaseProvider",
    "ModelResponse",
    "ProviderError",
    "ProviderRegistry",
    "get_provider",
    "get_registry",
]
