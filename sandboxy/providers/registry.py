"""Provider registry for managing multiple LLM providers."""

import logging
import os

from sandboxy.providers.base import BaseProvider, ModelInfo, ProviderError

logger = logging.getLogger(__name__)


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

    def __init__(self):
        """Initialize registry and detect available providers."""
        self.providers: dict[str, BaseProvider] = {}
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

        if not self.providers:
            logger.warning(
                "No providers available. Set at least one API key: "
                "OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
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

        # If model has a prefix (openai/gpt-4o format), use OpenRouter
        # This is OpenRouter's convention - direct APIs don't use prefixes
        if "/" in model_id:
            if "openrouter" in self.providers:
                return self.providers["openrouter"]
            # If no OpenRouter, try to extract and use direct provider
            provider_name, model_name = model_id.split("/", 1)
            if provider_name == "openai" and "openai" in self.providers:
                # Note: caller should strip prefix when calling direct provider
                return self.providers["openai"]
            if provider_name == "anthropic" and "anthropic" in self.providers:
                return self.providers["anthropic"]

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

        Returns deduplicated list with direct providers preferred
        over OpenRouter for overlapping models.
        """
        seen_ids: set[str] = set()
        models: list[ModelInfo] = []

        # Add direct provider models first (preferred)
        for name, provider in self.providers.items():
            if name == "openrouter":
                continue  # Add last

            for model in provider.list_models():
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


def get_provider(model_id: str) -> BaseProvider:
    """Get a provider for a model (convenience function).

    Args:
        model_id: Model identifier

    Returns:
        Provider that can handle the model

    """
    return get_registry().get_provider_for_model(model_id)
