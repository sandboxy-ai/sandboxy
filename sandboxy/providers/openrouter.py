"""OpenRouter provider - unified API for 400+ models."""

import os
import time
from typing import Any, AsyncIterator

import httpx

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError


# Popular models with their metadata (subset - OpenRouter has 400+)
OPENROUTER_MODELS = {
    # ==========================================================================
    # OpenAI
    # ==========================================================================
    "openai/gpt-4o": ModelInfo(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "openai/gpt-4o-mini": ModelInfo(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        supports_vision=True,
    ),
    "openai/o1": ModelInfo(
        id="openai/o1",
        name="o1",
        provider="openai",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=60.00,
    ),
    "openai/o1-mini": ModelInfo(
        id="openai/o1-mini",
        name="o1 Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=3.00,
        output_cost_per_million=12.00,
    ),
    # ==========================================================================
    # Anthropic
    # ==========================================================================
    "anthropic/claude-3.5-sonnet": ModelInfo(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "anthropic/claude-3.5-haiku": ModelInfo(
        id="anthropic/claude-3.5-haiku",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_vision=True,
    ),
    "anthropic/claude-3-opus": ModelInfo(
        id="anthropic/claude-3-opus",
        name="Claude 3 Opus",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    # ==========================================================================
    # Google
    # ==========================================================================
    "google/gemini-2.0-flash-exp:free": ModelInfo(
        id="google/gemini-2.0-flash-exp:free",
        name="Gemini 2.0 Flash (Free)",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        supports_vision=True,
    ),
    "google/gemini-2.0-flash-thinking-exp:free": ModelInfo(
        id="google/gemini-2.0-flash-thinking-exp:free",
        name="Gemini 2.0 Flash Thinking (Free)",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        supports_vision=True,
    ),
    "google/gemini-pro-1.5": ModelInfo(
        id="google/gemini-pro-1.5",
        name="Gemini Pro 1.5",
        provider="google",
        context_length=2000000,
        input_cost_per_million=1.25,
        output_cost_per_million=5.00,
        supports_vision=True,
    ),
    # ==========================================================================
    # xAI (Grok)
    # ==========================================================================
    "x-ai/grok-3": ModelInfo(
        id="x-ai/grok-3",
        name="Grok 3",
        provider="xai",
        context_length=131072,
        input_cost_per_million=0.30,
        output_cost_per_million=0.50,
    ),
    "x-ai/grok-3-mini": ModelInfo(
        id="x-ai/grok-3-mini",
        name="Grok 3 Mini",
        provider="xai",
        context_length=131072,
        input_cost_per_million=0.10,
        output_cost_per_million=0.20,
    ),
    # ==========================================================================
    # DeepSeek
    # ==========================================================================
    "deepseek/deepseek-chat": ModelInfo(
        id="deepseek/deepseek-chat",
        name="DeepSeek V3",
        provider="deepseek",
        context_length=64000,
        input_cost_per_million=0.14,
        output_cost_per_million=0.28,
    ),
    "deepseek/deepseek-r1": ModelInfo(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="deepseek",
        context_length=64000,
        input_cost_per_million=0.55,
        output_cost_per_million=2.19,
    ),
    # ==========================================================================
    # Meta (Llama)
    # ==========================================================================
    "meta-llama/llama-3.3-70b-instruct": ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.12,
        output_cost_per_million=0.30,
    ),
    "meta-llama/llama-3.1-405b-instruct": ModelInfo(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=2.00,
        output_cost_per_million=2.00,
    ),
    # ==========================================================================
    # Mistral
    # ==========================================================================
    "mistralai/mistral-large-2411": ModelInfo(
        id="mistralai/mistral-large-2411",
        name="Mistral Large",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=2.00,
        output_cost_per_million=6.00,
    ),
    "mistralai/mistral-small-2409": ModelInfo(
        id="mistralai/mistral-small-2409",
        name="Mistral Small",
        provider="mistral",
        context_length=32000,
        input_cost_per_million=0.20,
        output_cost_per_million=0.60,
    ),
    # ==========================================================================
    # Qwen
    # ==========================================================================
    "qwen/qwen-2.5-72b-instruct": ModelInfo(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.35,
        output_cost_per_million=0.40,
    ),
    "qwen/qwq-32b-preview": ModelInfo(
        id="qwen/qwq-32b-preview",
        name="QwQ 32B (Reasoning)",
        provider="qwen",
        context_length=32768,
        input_cost_per_million=0.12,
        output_cost_per_million=0.18,
    ),
    # ==========================================================================
    # Perplexity
    # ==========================================================================
    "perplexity/llama-3.1-sonar-large-128k-online": ModelInfo(
        id="perplexity/llama-3.1-sonar-large-128k-online",
        name="Sonar Large (Online)",
        provider="perplexity",
        context_length=128000,
        input_cost_per_million=1.00,
        output_cost_per_million=1.00,
    ),
}


class OpenRouterProvider(BaseProvider):
    """OpenRouter - unified API for 400+ models.

    OpenRouter provides access to models from OpenAI, Anthropic, Google,
    Meta, Mistral, and many others through a single API endpoint.

    No markup on provider pricing - you pay what you'd pay directly.
    """

    provider_name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None):
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key. If not provided, reads from
                     OPENROUTER_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "API key required. Set OPENROUTER_API_KEY or pass api_key.",
                provider=self.provider_name,
            )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sandboxy.ai",
            "X-Title": "Sandboxy Arena",
        }

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send completion request via OpenRouter."""
        start_time = time.time()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                error_body = e.response.text
                raise ProviderError(
                    f"HTTP {e.response.status_code}: {error_body}",
                    provider=self.provider_name,
                    model=model,
                ) from e
            except httpx.RequestError as e:
                raise ProviderError(
                    f"Request failed: {e}",
                    provider=self.provider_name,
                    model=model,
                ) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response data
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        # Calculate cost if we have token counts
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        return ModelResponse(
            content=message.get("content", ""),
            model_id=data.get("model", model),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream completion response."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError):
                            continue

    def list_models(self) -> list[ModelInfo]:
        """List popular models available through OpenRouter."""
        return list(OPENROUTER_MODELS.values())

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate cost in USD for a request."""
        model_info = OPENROUTER_MODELS.get(model)
        if not model_info or not model_info.input_cost_per_million:
            return None

        input_cost = (input_tokens / 1_000_000) * model_info.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * model_info.output_cost_per_million
        return round(input_cost + output_cost, 6)

    async def fetch_models(self) -> list[dict[str, Any]]:
        """Fetch full model list from OpenRouter API.

        Returns live model data including pricing and availability.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
