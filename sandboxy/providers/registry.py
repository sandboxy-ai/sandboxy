"""Provider registry for managing multiple LLM providers."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from sandboxy.providers.base import BaseProvider, ModelInfo, ProviderError

if TYPE_CHECKING:
    from sandboxy.providers.local import LocalProvider

logger = logging.getLogger(__name__)

# Local providers are lazily loaded to avoid circular imports
_local_providers: dict[str, LocalProvider] | None = None


def _get_local_providers() -> dict[str, BaseProvider]:
    """Load local providers from config file.

    Returns:
        Dict mapping provider name to LocalProvider instance

    """
    global _local_providers
    if _local_providers is not None:
        return _local_providers

    _local_providers = {}

    try:
        from sandboxy.providers.config import get_enabled_providers
        from sandboxy.providers.local import LocalProvider

        for config in get_enabled_providers():
            try:
                _local_providers[config.name] = LocalProvider(config)
                logger.info(f"Local provider '{config.name}' loaded from config")
            except Exception as e:
                logger.warning(f"Failed to load local provider '{config.name}': {e}")
    except Exception as e:
        logger.debug(f"Could not load local providers: {e}")

    return _local_providers


def reload_local_providers() -> None:
    """Force reload of local providers from config file."""
    global _local_providers
    _local_providers = None
    _get_local_providers()


class ProviderRegistry:
    """Registry of available LLM providers.

    Automatically detects available providers based on environment variables
    and provides unified access to models across all providers.

    Priority order:
    1. Direct providers (OpenAI, Anthropic) - lower latency
    2. OpenRouter - unified access to all models

    Example:
        registry = ProviderRegistry()
        provider = registry.get_provider_for_model("openai/gpt-4o")
        response = await provider.complete("openai/gpt-4o", messages)

    """

    def __init__(self, include_local: bool = True):
        """Initialize registry and detect available providers.

        Args:
            include_local: Whether to include local providers from config

        """
        self.providers: dict[str, BaseProvider] = {}
        self._include_local = include_local
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize providers based on available API keys."""
        # OpenRouter - unified provider (lower priority but covers all)
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                from sandboxy.providers.openrouter import OpenRouterProvider

                self.providers["openrouter"] = OpenRouterProvider()
                logger.info("OpenRouter provider initialized")
            except ProviderError as e:
                logger.warning(f"Failed to init OpenRouter: {e}")

        # Direct OpenAI (higher priority for OpenAI models)
        if os.getenv("OPENAI_API_KEY"):
            try:
                from sandboxy.providers.openai_provider import OpenAIProvider

                self.providers["openai"] = OpenAIProvider()
                logger.info("OpenAI provider initialized")
            except ProviderError as e:
                logger.warning(f"Failed to init OpenAI: {e}")

        # Direct Anthropic (higher priority for Claude models)
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from sandboxy.providers.anthropic_provider import AnthropicProvider

                self.providers["anthropic"] = AnthropicProvider()
                logger.info("Anthropic provider initialized")
            except ProviderError as e:
                logger.warning(f"Failed to init Anthropic: {e}")

        # Load local providers from config
        if self._include_local:
            local_providers = _get_local_providers()
            for name, provider in local_providers.items():
                self.providers[name] = provider
                logger.info(f"Local provider '{name}' registered")

        if not self.providers:
            logger.warning(
                "No providers available. Set at least one API key: "
                "OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY, "
                "or configure local providers with 'sandboxy providers add'"
            )

    def get_provider_for_model(self, model_id: str) -> BaseProvider:
        """Get the best provider for a given model.

        Model ID formats:
        - "provider/model" (e.g., "openai/gpt-4o") - OpenRouter format, use OpenRouter
        - "model" (e.g., "gpt-4o") - direct provider format, auto-select

        Args:
            model_id: Model identifier

        Returns:
            Provider instance that can handle the model

        Raises:
            ProviderError: If no provider available for the model

        """
        if not self.providers:
            raise ProviderError(
                "No providers configured. Set API key environment variables.",
                provider="registry",
            )

        # If model has a prefix (provider/model format)
        if "/" in model_id:
            provider_name, model_name = model_id.split("/", 1)

            # Priority 1: Check for LOCAL provider with matching name
            # Local providers take precedence over cloud providers
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                # Only use if it's a local provider (has config attribute)
                if hasattr(provider, "config"):
                    return provider

            # Priority 2: OpenRouter for provider/model format (e.g., "openai/gpt-4o")
            if "openrouter" in self.providers:
                return self.providers["openrouter"]

            # Priority 3: Fallback to direct cloud provider if available
            if provider_name == "openai" and "openai" in self.providers:
                return self.providers["openai"]
            if provider_name == "anthropic" and "anthropic" in self.providers:
                return self.providers["anthropic"]

            # No valid provider found for prefixed model - raise clear error
            available = list(self.providers.keys())
            raise ProviderError(
                f"No provider available for model '{model_id}'. "
                f"The '{provider_name}/' prefix requires OpenRouter (set OPENROUTER_API_KEY) "
                f"or a local provider named '{provider_name}'. "
                f"Available providers: {available}",
                provider="registry",
            )

        # No prefix - use direct providers
        model_lower = model_id.lower()

        # OpenAI models (direct format: gpt-4o, not openai/gpt-4o)
        if any(m in model_lower for m in ["gpt-4", "gpt-5", "o1", "o3"]):
            if "openai" in self.providers:
                return self.providers["openai"]
            if "openrouter" in self.providers:
                return self.providers["openrouter"]

        # Anthropic models (direct format: claude-3-opus, not anthropic/claude-3-opus)
        if "claude" in model_lower:
            if "anthropic" in self.providers:
                return self.providers["anthropic"]
            if "openrouter" in self.providers:
                return self.providers["openrouter"]

        # Default to OpenRouter if available (covers most models)
        if "openrouter" in self.providers:
            return self.providers["openrouter"]

        # Last resort - return first available provider
        return next(iter(self.providers.values()))

    def list_all_models(self) -> list[ModelInfo]:
        """List all models from all providers.

        Returns deduplicated list with:
        1. Local providers first (highest priority)
        2. Direct cloud providers (OpenAI, Anthropic)
        3. OpenRouter last (fallback)
        """
        seen_ids: set[str] = set()
        models: list[ModelInfo] = []

        # Add local provider models first (highest priority)
        for name, provider in self.providers.items():
            if name in ("openrouter", "openai", "anthropic"):
                continue

            for model in provider.list_models():
                # Use provider-prefixed ID for local models
                prefixed_id = f"{name}/{model.id}"
                if prefixed_id not in seen_ids:
                    seen_ids.add(prefixed_id)
                    models.append(model)

        # Add direct cloud provider models
        for name in ("openai", "anthropic"):
            if name not in self.providers:
                continue

            for model in self.providers[name].list_models():
                if model.id not in seen_ids:
                    seen_ids.add(model.id)
                    models.append(model)

        # Add OpenRouter models (for ones not covered by direct)
        if "openrouter" in self.providers:
            for model in self.providers["openrouter"].list_models():
                if model.id not in seen_ids:
                    seen_ids.add(model.id)
                    models.append(model)

        return models

    def get_local_providers(self) -> dict[str, BaseProvider]:
        """Get all local providers.

        Returns:
            Dict of local provider name to provider instance

        """
        return {
            name: provider
            for name, provider in self.providers.items()
            if hasattr(provider, "config")  # LocalProvider has config attribute
        }

    def get_provider(self, provider_name: str) -> BaseProvider | None:
        """Get a specific provider by name.

        Args:
            provider_name: Provider name (openai, anthropic, openrouter)

        Returns:
            Provider instance or None if not available

        """
        return self.providers.get(provider_name)

    @property
    def available_providers(self) -> list[str]:
        """List names of available providers."""
        return list(self.providers.keys())


# Global registry instance
_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global provider registry.

    Forces re-initialization on next get_registry() call.
    Useful after loading new environment variables.
    """
    global _registry
    _registry = None


def get_provider(model_id: str) -> BaseProvider:
    """Get a provider for a model (convenience function).

    Args:
        model_id: Model identifier

    Returns:
        Provider that can handle the model

    """
    return get_registry().get_provider_for_model(model_id)
