"""Direct Anthropic provider."""

import os
import time
from collections.abc import AsyncIterator
from typing import Any

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError

ANTHROPIC_MODELS = {
    # Claude 4.5 Series (latest)
    "claude-opus-4-5-20251101": ModelInfo(
        id="claude-opus-4-5-20251101",
        name="Claude Opus 4.5",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    "claude-haiku-4-5-20251101": ModelInfo(
        id="claude-haiku-4-5-20251101",
        name="Claude Haiku 4.5",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_vision=True,
    ),
    # Claude 4 Series
    "claude-sonnet-4-20250514": ModelInfo(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "claude-opus-4-20250514": ModelInfo(
        id="claude-opus-4-20250514",
        name="Claude Opus 4",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    # Claude 3.5 Series
    "claude-3-5-sonnet-20241022": ModelInfo(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "claude-3-5-haiku-20241022": ModelInfo(
        id="claude-3-5-haiku-20241022",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_vision=True,
    ),
    # Claude 3 Series (legacy)
    "claude-3-opus-20240229": ModelInfo(
        id="claude-3-opus-20240229",
        name="Claude 3 Opus",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    "claude-3-haiku-20240307": ModelInfo(
        id="claude-3-haiku-20240307",
        name="Claude 3 Haiku",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        supports_vision=True,
    ),
}

# Aliases for common model names
MODEL_ALIASES = {
    # Claude 4.5
    "claude-opus-4.5": "claude-opus-4-5-20251101",
    "claude-opus-4-5": "claude-opus-4-5-20251101",
    "claude-haiku-4.5": "claude-haiku-4-5-20251101",
    "claude-haiku-4-5": "claude-haiku-4-5-20251101",
    # Claude 4
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-opus-4": "claude-opus-4-20250514",
    # Claude 3.5
    "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3.5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    # Claude 3
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
}


class AnthropicProvider(BaseProvider):
    """Direct Anthropic API provider.

    Use this when you have an Anthropic API key and want to call
    Claude models directly.
    """

    provider_name = "anthropic"

    def __init__(self, api_key: str | None = None):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key. If not provided, reads from
                     ANTHROPIC_API_KEY environment variable.

        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "API key required. Set ANTHROPIC_API_KEY or pass api_key.",
                provider=self.provider_name,
            )

        # Lazy import to avoid requiring anthropic package if not used
        try:
            from anthropic import AsyncAnthropic

            self.client = AsyncAnthropic(api_key=self.api_key)
        except ImportError as e:
            raise ProviderError(
                "anthropic package required. Install with: pip install anthropic",
                provider=self.provider_name,
            ) from e

    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full model ID."""
        return MODEL_ALIASES.get(model, model)

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send completion request to Anthropic."""
        start_time = time.time()
        resolved_model = self._resolve_model(model)

        # Convert from OpenAI format to Anthropic format
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )

        try:
            response = await self.client.messages.create(
                model=resolved_model,
                messages=anthropic_messages,
                system=system_prompt or "",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception as e:
            raise ProviderError(
                str(e),
                provider=self.provider_name,
                model=model,
            ) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract content from response
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self._calculate_cost(resolved_model, input_tokens, output_tokens)

        return ModelResponse(
            content=content,
            model_id=response.model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            finish_reason=response.stop_reason,
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
        """Stream completion response from Anthropic."""
        resolved_model = self._resolve_model(model)

        # Convert from OpenAI format to Anthropic format
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )

        try:
            async with self.client.messages.stream(
                model=resolved_model,
                messages=anthropic_messages,
                system=system_prompt or "",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise ProviderError(
                str(e),
                provider=self.provider_name,
                model=model,
            ) from e

    def list_models(self) -> list[ModelInfo]:
        """List available Anthropic models."""
        return list(ANTHROPIC_MODELS.values())

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate cost in USD for a request."""
        model_info = ANTHROPIC_MODELS.get(model)
        if not model_info or not model_info.input_cost_per_million:
            return None

        input_cost = (input_tokens / 1_000_000) * model_info.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * (model_info.output_cost_per_million or 0)
        return round(input_cost + output_cost, 6)
