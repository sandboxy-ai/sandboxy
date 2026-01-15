"""Mock LLM providers for testing.

This module provides mock implementations of LLM providers that can be used
in tests without making real API calls. The mocks track call history and
allow configurable responses and failure scenarios.

Usage:
    # Basic usage
    provider = MockOpenRouterProvider(responses=["Hello!", "World!"])
    result = await provider.complete("model", messages)
    assert result.content == "Hello!"

    # With failure simulation
    provider = MockOpenRouterProvider(should_fail=True, failure_message="Rate limited")
    with pytest.raises(ProviderError):
        await provider.complete("model", messages)

    # Track calls
    provider = MockOpenRouterProvider()
    await provider.complete("model", messages)
    assert len(provider.call_history) == 1
"""

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError


class MockOpenRouterProvider(BaseProvider):
    """Mock OpenRouter provider for testing.

    Features:
    - Configurable response sequences
    - Failure simulation
    - Call history tracking
    - Token counting simulation
    - Cost calculation

    Attributes:
        call_history: List of all calls made to complete()
        response_index: Current position in response sequence

    """

    provider_name = "openrouter"

    def __init__(
        self,
        responses: list[str] | None = None,
        should_fail: bool = False,
        failure_message: str = "Mock provider error",
        latency_ms: int = 100,
        token_multiplier: float = 0.25,  # Tokens per character
    ) -> None:
        """Initialize the mock provider.

        Args:
            responses: List of response strings to return in sequence
            should_fail: Whether to raise ProviderError on calls
            failure_message: Error message when failing
            latency_ms: Simulated latency to return
            token_multiplier: Factor to convert content length to tokens

        """
        self.responses = responses or ["Mock response"]
        self.response_index = 0
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.latency_ms = latency_ms
        self.token_multiplier = token_multiplier
        self.call_history: list[dict[str, Any]] = []

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Simulate a completion request.

        Args:
            model: Model ID
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Returns:
            ModelResponse with mock content

        Raises:
            ProviderError: If should_fail is True

        """
        # Record the call
        self.call_history.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }
        )

        if self.should_fail:
            raise ProviderError(
                self.failure_message,
                provider=self.provider_name,
                model=model,
            )

        # Get next response (cycling through if exhausted)
        response_content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        # Simulate token counts
        input_text = str(messages)
        input_tokens = int(len(input_text) * self.token_multiplier)
        output_tokens = int(len(response_content) * self.token_multiplier)

        return ModelResponse(
            content=response_content,
            model_id=model,
            latency_ms=self.latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Simulate a streaming completion.

        Yields response word by word.
        """
        response = await self.complete(model, messages, **kwargs)
        for word in response.content.split():
            yield word + " "

    def list_models(self) -> list[ModelInfo]:
        """Return a list of mock models."""
        return [
            ModelInfo(
                id="openai/gpt-4o",
                name="GPT-4o",
                provider="openai",
                context_length=128000,
                input_cost_per_million=2.50,
                output_cost_per_million=10.00,
            ),
            ModelInfo(
                id="anthropic/claude-3.5-sonnet",
                name="Claude 3.5 Sonnet",
                provider="anthropic",
                context_length=200000,
                input_cost_per_million=3.00,
                output_cost_per_million=15.00,
            ),
        ]

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate mock cost based on typical OpenRouter pricing."""
        # Using GPT-4o pricing as default
        input_cost = (input_tokens / 1_000_000) * 2.50
        output_cost = (output_tokens / 1_000_000) * 10.00
        return round(input_cost + output_cost, 6)

    def reset(self) -> None:
        """Reset the provider state."""
        self.response_index = 0
        self.call_history.clear()

    @property
    def total_calls(self) -> int:
        """Return total number of calls made."""
        return len(self.call_history)

    @property
    def last_call(self) -> dict[str, Any] | None:
        """Return the last call made, or None if no calls."""
        return self.call_history[-1] if self.call_history else None


class MockOpenAIProvider(BaseProvider):
    """Mock OpenAI provider for testing direct OpenAI API calls."""

    provider_name = "openai"

    def __init__(
        self,
        responses: list[str] | None = None,
        should_fail: bool = False,
        failure_message: str = "Mock OpenAI error",
    ) -> None:
        self.responses = responses or ["Mock OpenAI response"]
        self.response_index = 0
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.call_history: list[dict[str, Any]] = []

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ModelResponse:
        self.call_history.append(
            {
                "model": model,
                "messages": messages,
                **kwargs,
            }
        )

        if self.should_fail:
            raise ProviderError(
                self.failure_message,
                provider=self.provider_name,
                model=model,
            )

        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        return ModelResponse(
            content=content,
            model_id=model,
            latency_ms=50,
            input_tokens=100,
            output_tokens=50,
        )

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                provider="openai",
                context_length=128000,
            )
        ]


class MockAnthropicProvider(BaseProvider):
    """Mock Anthropic provider for testing direct Anthropic API calls."""

    provider_name = "anthropic"

    def __init__(
        self,
        responses: list[str] | None = None,
        should_fail: bool = False,
        failure_message: str = "Mock Anthropic error",
    ) -> None:
        self.responses = responses or ["Mock Anthropic response"]
        self.response_index = 0
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.call_history: list[dict[str, Any]] = []

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ModelResponse:
        self.call_history.append(
            {
                "model": model,
                "messages": messages,
                **kwargs,
            }
        )

        if self.should_fail:
            raise ProviderError(
                self.failure_message,
                provider=self.provider_name,
                model=model,
            )

        content = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        return ModelResponse(
            content=content,
            model_id=model,
            latency_ms=75,
            input_tokens=80,
            output_tokens=40,
        )

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider="anthropic",
                context_length=200000,
            )
        ]


class MockProviderRegistry:
    """Mock provider registry for testing.

    Allows configuring which provider to return for different models
    and tracks provider lookup calls.
    """

    def __init__(
        self,
        default_responses: list[str] | None = None,
        provider_map: dict[str, BaseProvider] | None = None,
    ) -> None:
        """Initialize the mock registry.

        Args:
            default_responses: Default responses for the default provider
            provider_map: Map of model prefixes to specific providers

        """
        self._default_provider = MockOpenRouterProvider(responses=default_responses)
        self._provider_map = provider_map or {}
        self.providers = {"openrouter": self._default_provider}
        self.available_providers = ["openrouter"]
        self.lookup_history: list[str] = []

    def get_provider_for_model(self, model: str) -> BaseProvider:
        """Get provider for a model, tracking the lookup.

        Args:
            model: Model ID

        Returns:
            Provider instance

        """
        self.lookup_history.append(model)

        # Check specific provider map first
        for prefix, provider in self._provider_map.items():
            if model.startswith(prefix):
                return provider
        return self._default_provider

    def list_all_models(self) -> list[ModelInfo]:
        """List all models from all providers."""
        return self._default_provider.list_models()

    def add_provider(self, prefix: str, provider: BaseProvider) -> None:
        """Add a provider for a model prefix."""
        self._provider_map[prefix] = provider
        self.providers[provider.provider_name] = provider

    def reset(self) -> None:
        """Reset registry state."""
        self._default_provider.reset()
        self.lookup_history.clear()


def create_mock_openai_client(
    responses: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock OpenAI client for LlmPromptAgent testing.

    This mocks the OpenAI SDK client used by LlmPromptAgent, allowing
    tests to run without API keys.

    Args:
        responses: List of response dicts with choices and usage
        tool_calls: Tool calls to include in responses

    Returns:
        MagicMock that behaves like openai.OpenAI client

    Usage:
        mock_client = create_mock_openai_client(
            responses=[{"choices": [{"message": {"content": "Hello"}}]}]
        )
        with patch("openai.OpenAI", return_value=mock_client):
            agent = LlmPromptAgent(config)
            action = agent.step(history)

    """
    mock_client = MagicMock()

    default_response = {
        "choices": [
            {
                "message": {
                    "content": "Mock OpenAI response",
                    "tool_calls": tool_calls,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
        },
    }

    # Build response sequence
    response_sequence = []
    for resp in responses or [default_response]:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        message_data = resp.get("choices", [{}])[0].get("message", {})
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = message_data.get("content", "")
        mock_response.choices[0].message.tool_calls = message_data.get("tool_calls")
        mock_response.choices[0].finish_reason = resp.get("choices", [{}])[0].get(
            "finish_reason", "stop"
        )

        usage_data = resp.get("usage", {})
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = usage_data.get("prompt_tokens", 50)
        mock_response.usage.completion_tokens = usage_data.get("completion_tokens", 100)

        response_sequence.append(mock_response)

    # If only one response, return it always; otherwise cycle through
    if len(response_sequence) == 1:
        mock_client.chat.completions.create = MagicMock(return_value=response_sequence[0])
    else:
        mock_client.chat.completions.create = MagicMock(side_effect=response_sequence)

    return mock_client


def create_mock_tool_call(
    id: str = "call_abc123",
    name: str = "shopify__get_order",
    arguments: str = '{"order_id": "ORD123"}',
) -> MagicMock:
    """Create a mock tool call object as returned by OpenAI.

    Args:
        id: Tool call ID
        name: Function name (tool__action format)
        arguments: JSON string of arguments

    Returns:
        MagicMock representing a tool call

    """
    mock_tool_call = MagicMock()
    mock_tool_call.id = id
    mock_tool_call.function = MagicMock()
    mock_tool_call.function.name = name
    mock_tool_call.function.arguments = arguments
    return mock_tool_call
