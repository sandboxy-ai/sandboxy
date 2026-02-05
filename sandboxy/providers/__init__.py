"""Multi-model provider abstraction layer.

Supports multiple LLM providers through a unified interface:
- OpenRouter (400+ models via single API)
- OpenAI (direct)
- Anthropic (direct)
- Local providers (Ollama, LM Studio, vLLM, OpenAI-compatible)

Usage:
    from sandboxy.providers import get_provider, ProviderRegistry

    # Get provider for a specific model
    provider = get_provider("openai/gpt-4o")
    response = await provider.complete("openai/gpt-4o", messages)

    # Or use the registry for local models
    registry = ProviderRegistry()
    provider = registry.get_provider_for_model("ollama/llama3")
"""

from sandboxy.providers.base import (
    BaseProvider,
    ModelInfo,
    ModelResponse,
    ProviderError,
)
from sandboxy.providers.config import (
    LocalModelInfo,
    LocalProviderConfig,
    ProvidersConfigFile,
    ProviderStatus,
    ProviderStatusEnum,
    get_enabled_providers,
    load_providers_config,
    save_providers_config,
)
from sandboxy.providers.local import LocalProvider, LocalProviderConnectionError
from sandboxy.providers.registry import (
    ProviderRegistry,
    get_provider,
    get_registry,
    reload_local_providers,
    reset_registry,
)

__all__ = [
    # Base types
    "BaseProvider",
    "ModelInfo",
    "ModelResponse",
    "ProviderError",
    # Registry
    "ProviderRegistry",
    "get_provider",
    "get_registry",
    "reload_local_providers",
    "reset_registry",
    # Local provider
    "LocalProvider",
    "LocalProviderConnectionError",
    "LocalProviderConfig",
    "LocalModelInfo",
    "ProvidersConfigFile",
    "ProviderStatus",
    "ProviderStatusEnum",
    # Config functions
    "load_providers_config",
    "save_providers_config",
    "get_enabled_providers",
]
