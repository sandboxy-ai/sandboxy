"""Direct OpenAI provider."""

import os
import time
from collections.abc import AsyncIterator
from typing import Any

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError

OPENAI_MODELS = {
    # GPT-5.2 Series (latest)
    "gpt-5.2-pro": ModelInfo(
        id="gpt-5.2-pro",
        name="GPT-5.2 Pro",
        provider="openai",
        context_length=200000,
        input_cost_per_million=5.00,
        output_cost_per_million=20.00,
        supports_vision=True,
    ),
    "gpt-5.2": ModelInfo(
        id="gpt-5.2",
        name="GPT-5.2",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "gpt-5.2-chat": ModelInfo(
        id="gpt-5.2-chat",
        name="GPT-5.2 Chat",
        provider="openai",
        context_length=128000,
        input_cost_per_million=1.00,
        output_cost_per_million=4.00,
        supports_vision=True,
    ),
    # GPT-5.1 Series
    "gpt-5.1": ModelInfo(
        id="gpt-5.1",
        name="GPT-5.1",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.00,
        output_cost_per_million=8.00,
        supports_vision=True,
    ),
    "gpt-5.1-codex": ModelInfo(
        id="gpt-5.1-codex",
        name="GPT-5.1 Codex",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
    ),
    # GPT-5 Series
    "gpt-5": ModelInfo(
        id="gpt-5",
        name="GPT-5",
        provider="openai",
        context_length=128000,
        input_cost_per_million=5.00,
        output_cost_per_million=20.00,
    ),
    "gpt-5-image": ModelInfo(
        id="gpt-5-image",
        name="GPT-5 Image",
        provider="openai",
        context_length=128000,
        input_cost_per_million=3.00,
        output_cost_per_million=12.00,
        supports_vision=True,
    ),
    "gpt-5-mini": ModelInfo(
        id="gpt-5-mini",
        name="GPT-5 Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=1.00,
        output_cost_per_million=4.00,
    ),
    "gpt-5-nano": ModelInfo(
        id="gpt-5-nano",
        name="GPT-5 Nano",
        provider="openai",
        context_length=128000,
        input_cost_per_million=0.50,
        output_cost_per_million=2.00,
    ),
    # o-Series (Reasoning)
    "o3-deep-research": ModelInfo(
        id="o3-deep-research",
        name="o3 Deep Research",
        provider="openai",
        context_length=200000,
        input_cost_per_million=20.00,
        output_cost_per_million=80.00,
    ),
    "o1": ModelInfo(
        id="o1",
        name="o1",
        provider="openai",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=60.00,
    ),
    "o1-mini": ModelInfo(
        id="o1-mini",
        name="o1 Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=3.00,
        output_cost_per_million=12.00,
    ),
    # GPT-4 Series (legacy)
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        supports_vision=True,
    ),
}


class OpenAIProvider(BaseProvider):
    """Direct OpenAI API provider.

    Use this when you have an OpenAI API key and want to call
    OpenAI models directly (potentially lower latency than OpenRouter).
    """

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. If not provided, reads from
                     OPENAI_API_KEY environment variable.

        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "API key required. Set OPENAI_API_KEY or pass api_key.",
                provider=self.provider_name,
            )

        # Lazy import to avoid requiring openai package if not used
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError as e:
            raise ProviderError(
                "openai package required. Install with: pip install openai",
                provider=self.provider_name,
            ) from e

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send completion request to OpenAI."""
        start_time = time.time()

        # Handle model-specific parameters
        completion_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        # GPT-5 (all variants) and o1/o3 reasoning models don't support temperature
        if not any(x in model for x in ["gpt-5", "o1", "o3"]):
            completion_kwargs["temperature"] = temperature

        # GPT-5 models use max_completion_tokens
        if "gpt-5" in model or "gpt-4o" in model:
            completion_kwargs["max_completion_tokens"] = max_tokens
        else:
            completion_kwargs["max_tokens"] = max_tokens

        # Add any extra kwargs
        completion_kwargs.update(kwargs)

        try:
            response = await self.client.chat.completions.create(**completion_kwargs)
        except Exception as e:
            raise ProviderError(
                str(e),
                provider=self.provider_name,
                model=model,
            ) from e

        latency_ms = int((time.time() - start_time) * 1000)

        choice = response.choices[0]
        usage = response.usage

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        return ModelResponse(
            content=choice.message.content or "",
            model_id=response.model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump(),
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream completion response from OpenAI."""
        completion_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        # GPT-5 (all variants) and o1/o3 reasoning models don't support temperature
        if not any(x in model for x in ["gpt-5", "o1", "o3"]):
            completion_kwargs["temperature"] = temperature

        if "gpt-5" in model or "gpt-4o" in model:
            completion_kwargs["max_completion_tokens"] = max_tokens
        else:
            completion_kwargs["max_tokens"] = max_tokens

        completion_kwargs.update(kwargs)

        try:
            stream = await self.client.chat.completions.create(**completion_kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise ProviderError(
                str(e),
                provider=self.provider_name,
                model=model,
            ) from e

    def list_models(self) -> list[ModelInfo]:
        """List available OpenAI models."""
        return list(OPENAI_MODELS.values())

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate cost in USD for a request."""
        model_info = OPENAI_MODELS.get(model)
        if not model_info or not model_info.input_cost_per_million:
            return None

        input_cost = (input_tokens / 1_000_000) * model_info.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * (model_info.output_cost_per_million or 0)
        return round(input_cost + output_cost, 6)
