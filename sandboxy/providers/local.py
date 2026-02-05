"""Local model provider for OpenAI-compatible servers (Ollama, LM Studio, vLLM, etc.)."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError
from sandboxy.providers.config import (
    LocalModelInfo,
    LocalProviderConfig,
    ProviderStatus,
    ProviderStatusEnum,
)

logger = logging.getLogger(__name__)

# Default timeout for requests (60 seconds)
DEFAULT_TIMEOUT = 60.0


class LocalProviderConnectionError(ProviderError):
    """Error when local provider is unreachable."""

    def __init__(self, provider_name: str, base_url: str, original_error: str):
        self.base_url = base_url
        self.original_error = original_error
        message = (
            f"Cannot connect to {provider_name} at {base_url}. "
            f"Is the server running? Error: {original_error}"
        )
        super().__init__(message, provider=provider_name)


class LocalProvider(BaseProvider):
    """Provider for local OpenAI-compatible servers.

    Supports:
    - Ollama (http://localhost:11434/v1)
    - LM Studio (http://localhost:1234/v1)
    - vLLM (http://localhost:8000/v1)
    - Any OpenAI-compatible endpoint

    """

    provider_name: str = "local"

    def __init__(self, config: LocalProviderConfig):
        """Initialize local provider with configuration.

        Args:
            config: Provider configuration including base URL and optional API key

        """
        self.config = config
        self.provider_name = config.name

        # Build headers
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

        # Cache for discovered models
        self._models_cache: list[LocalModelInfo] | None = None
        self._tool_support_cache: dict[str, bool] = {}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send a chat completion request to the local server.

        Args:
            model: Model identifier (e.g., "llama3:8b", "mistral:latest")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions for function calling
            **kwargs: Additional parameters passed to the API

        Returns:
            ModelResponse with content and metadata

        Raises:
            LocalProviderConnectionError: If server is unreachable
            ProviderError: If the request fails

        """
        # Strip provider prefix if present (e.g., "ollama/llama3" -> "llama3")
        if "/" in model:
            _, model = model.rsplit("/", 1)

        start_time = time.perf_counter()

        # Build request payload
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Add tools if provided and model might support them
        if tools:
            payload["tools"] = tools

        # Merge any default params from config
        payload.update(self.config.default_params)
        payload.update(kwargs)

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as e:
            raise LocalProviderConnectionError(
                self.config.name,
                self.config.base_url,
                str(e),
            ) from e
        except httpx.HTTPStatusError as e:
            error_detail = self._extract_error_detail(e)
            raise ProviderError(
                f"Request failed: {error_detail}",
                provider=self.config.name,
                model=model,
            ) from e
        except httpx.TimeoutException as e:
            raise ProviderError(
                f"Request timed out after {DEFAULT_TIMEOUT}s",
                provider=self.config.name,
                model=model,
            ) from e

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract response content
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Handle tool calls in response
        tool_calls = message.get("tool_calls")
        if tool_calls:
            # Include tool calls in raw response for caller to handle
            pass

        # Extract token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # If no usage provided, estimate with tiktoken
        if input_tokens == 0 and output_tokens == 0:
            input_tokens, output_tokens = self._estimate_tokens(messages, content)

        return ModelResponse(
            content=content,
            model_id=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,  # Local models have no API cost
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.

        Args:
            model: Model identifier
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Yields:
            Content chunks as they arrive

        """
        # Strip provider prefix if present
        if "/" in model:
            _, model = model.rsplit("/", 1)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        payload.update(self.config.default_params)
        payload.update(kwargs)

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break

                    try:
                        import json

                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

        except httpx.ConnectError as e:
            raise LocalProviderConnectionError(
                self.config.name,
                self.config.base_url,
                str(e),
            ) from e

    def list_models(self) -> list[ModelInfo]:
        """Return available models from this provider.

        Returns cached list if available. Call refresh_models() to update.

        """
        if self._models_cache is not None:
            return self._models_cache

        # Return manually configured models if any
        if self.config.models:
            return [
                LocalModelInfo(
                    id=model_id,
                    name=model_id,
                    provider=self.config.name,
                    provider_name=self.config.name,
                    context_length=8192,  # Default, unknown
                    input_cost_per_million=None,
                    output_cost_per_million=None,
                    supports_tools=False,  # Unknown until verified
                    supports_vision=False,
                    supports_streaming=True,
                    is_local=True,
                    capabilities_verified=False,
                )
                for model_id in self.config.models
            ]

        # Return empty list - caller should use async refresh_models()
        return []

    async def refresh_models(self) -> list[LocalModelInfo]:
        """Fetch available models from the provider's /v1/models endpoint.

        Returns:
            List of discovered models

        """
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()

            models: list[LocalModelInfo] = []

            # Handle different response formats:
            # - OpenAI format: {"data": [...]}
            # - Ollama format: {"models": [...]} or direct list
            model_list = data.get("data") or data.get("models") or []
            if model_list is None:
                model_list = []

            # If data itself is a list (some providers return this)
            if isinstance(data, list):
                model_list = data

            for model_data in model_list:
                # Handle different model object formats
                if isinstance(model_data, str):
                    # Some providers return just model IDs as strings
                    model_id = model_data
                    model_name = model_data
                    context_length = 8192
                else:
                    # Object format - try various field names
                    model_id = (
                        model_data.get("id")
                        or model_data.get("model")
                        or model_data.get("name")
                        or "unknown"
                    )
                    model_name = model_data.get("name", model_id)
                    context_length = model_data.get("context_length", 8192)

                models.append(
                    LocalModelInfo(
                        id=model_id,
                        name=model_name,
                        provider=self.config.name,
                        provider_name=self.config.name,
                        context_length=context_length,
                        input_cost_per_million=None,
                        output_cost_per_million=None,
                        supports_tools=self._infer_tool_support(model_id),
                        supports_vision=False,
                        supports_streaming=True,
                        is_local=True,
                        capabilities_verified=False,
                    )
                )

            self._models_cache = models
            return models

        except httpx.ConnectError as e:
            raise LocalProviderConnectionError(
                self.config.name,
                self.config.base_url,
                str(e),
            ) from e
        except Exception as e:
            logger.warning(f"Failed to fetch models from {self.config.name}: {e}")
            # Return manually configured models as fallback
            return self.list_models()

    def supports_model(self, model_id: str) -> bool:
        """Check if this provider supports a given model.

        Args:
            model_id: Model identifier to check

        Returns:
            True if the model is supported

        """
        # Strip provider prefix if present
        if "/" in model_id:
            prefix, model_name = model_id.rsplit("/", 1)
            if prefix != self.config.name:
                return False
            model_id = model_name

        # Check manually configured models
        if self.config.models:
            return model_id in self.config.models

        # Check cached models
        if self._models_cache:
            return any(m.id == model_id for m in self._models_cache)

        # If no cache, assume we support it (will fail at runtime if not)
        return True

    async def test_connection(self) -> ProviderStatus:
        """Test connectivity to the provider and return status.

        Returns:
            ProviderStatus with connection details

        """
        from datetime import datetime

        start_time = time.perf_counter()

        try:
            models = await self.refresh_models()
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            return ProviderStatus(
                name=self.config.name,
                status=ProviderStatusEnum.CONNECTED,
                last_checked=datetime.now(),
                available_models=[m.id for m in models],
                latency_ms=latency_ms,
            )

        except LocalProviderConnectionError as e:
            return ProviderStatus(
                name=self.config.name,
                status=ProviderStatusEnum.DISCONNECTED,
                last_checked=datetime.now(),
                error_message=str(e),
            )
        except Exception as e:
            return ProviderStatus(
                name=self.config.name,
                status=ProviderStatusEnum.ERROR,
                last_checked=datetime.now(),
                error_message=str(e),
            )

    def _extract_error_detail(self, error: httpx.HTTPStatusError) -> str:
        """Extract error detail from HTTP error response."""
        try:
            data = error.response.json()
            if "error" in data:
                err = data["error"]
                if isinstance(err, dict):
                    return err.get("message", str(err))
                return str(err)
        except Exception:
            logger.debug("Failed to parse error response JSON")
        return f"HTTP {error.response.status_code}"

    def _estimate_tokens(
        self, messages: list[dict[str, Any]], response_content: str
    ) -> tuple[int, int]:
        """Estimate token counts using tiktoken when server doesn't provide them.

        Args:
            messages: Input messages
            response_content: Output content

        Returns:
            Tuple of (input_tokens, output_tokens)

        """
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")

            # Estimate input tokens
            input_text = ""
            for msg in messages:
                input_text += msg.get("role", "") + " " + msg.get("content", "") + " "
            input_tokens = len(enc.encode(input_text))

            # Estimate output tokens
            output_tokens = len(enc.encode(response_content))

            return input_tokens, output_tokens
        except ImportError:
            # tiktoken not available, return rough estimates
            input_chars = sum(len(str(m.get("content", ""))) for m in messages)
            return input_chars // 4, len(response_content) // 4

    def _infer_tool_support(self, model_id: str) -> bool:
        """Infer whether a model likely supports tool calling.

        Based on known models that support function calling.

        """
        # Check cache first
        if model_id in self._tool_support_cache:
            return self._tool_support_cache[model_id]

        model_lower = model_id.lower()

        # Models known to support tools
        tool_supporting_patterns = [
            "llama3.1",
            "llama-3.1",
            "llama3.2",
            "llama-3.2",
            "mistral",
            "mixtral",
            "qwen",
            "command-r",
            "gemma2",
        ]

        supports = any(pattern in model_lower for pattern in tool_supporting_patterns)
        self._tool_support_cache[model_id] = supports
        return supports
