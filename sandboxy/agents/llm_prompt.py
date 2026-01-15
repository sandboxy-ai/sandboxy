"""LLM-based prompt agent using OpenAI SDK."""

import json
import logging
import os
import time
from typing import Any

from sandboxy.agents.base import AgentAction, AgentConfig, BaseAgent
from sandboxy.core.state import Message

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds


class LlmPromptAgent(BaseAgent):
    """Agent that uses an LLM via OpenAI-compatible API.

    Supports both direct OpenAI and OpenRouter (for 400+ models).
    Uses OpenRouter when model contains "/" (e.g., "openai/gpt-4o").
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self._client: Any = None
        self._is_openrouter = "/" in (config.model or "")
        # Token usage tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def api_key(self) -> str:
        """Get the appropriate API key based on model type."""
        if self._is_openrouter:
            return os.getenv("OPENROUTER_API_KEY", "")
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI client with appropriate configuration."""
        if self._client is None:
            from openai import OpenAI

            if self._is_openrouter:
                logger.debug("Initializing OpenRouter client for model: %s", self.config.model)
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
            else:
                logger.debug("Initializing OpenAI client for model: %s", self.config.model)
                self._client = OpenAI(api_key=self.api_key)
        return self._client

    def step(
        self,
        history: list[Message],
        available_tools: list[dict[str, Any]] | None = None,
    ) -> AgentAction:
        """Process conversation and return next action using LLM."""
        if not self.api_key:
            return self._stub_response(history)

        messages = self._build_messages(history)
        tools = self._build_tools(available_tools) if available_tools else None

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._call_api(messages, tools)
                return self._parse_response(response)
            except Exception as e:
                last_error = e
                is_retryable = self._is_retryable_error(e)

                if is_retryable and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2**attempt)
                    logger.warning(
                        "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                else:
                    logger.error("Error calling LLM: %s", e, exc_info=True)
                    break

        return AgentAction(
            type="message",
            content=f"Error calling LLM: {last_error}",
        )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        error_str = str(error).lower()
        retryable_patterns = [
            "rate limit",
            "timeout",
            "connection",
            "503",
            "502",
            "500",
            "overloaded",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)

    def _build_messages(self, history: list[Message]) -> list[dict[str, Any]]:
        """Convert history to OpenAI message format."""
        messages: list[dict[str, Any]] = []

        if self.config.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self.config.system_prompt,
                }
            )

        for msg in history:
            if msg.role == "tool":
                messages.append(
                    {
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id or msg.tool_name or "unknown",
                    }
                )
            elif msg.role == "assistant" and msg.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": tc.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )
            else:
                messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return messages

    def _build_tools(self, available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build OpenAI tools format from available tools."""
        tools = []
        for tool in available_tools:
            actions = tool.get("actions", [])
            for action in actions:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"{tool['name']}__{action['name']}",
                            "description": action.get("description", ""),
                            "parameters": action.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        },
                    }
                )
        return tools

    def _call_api(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        """Make API call to OpenAI/OpenRouter."""
        model = self.config.model or "gpt-4o-mini"
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        # Add temperature (some models don't support it)
        if "nano" not in model.lower():
            kwargs["temperature"] = self.config.params.get("temperature", 0.7)

        # Add max tokens
        max_tokens = self.config.params.get("max_tokens", 2048)
        kwargs["max_completion_tokens"] = max_tokens

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)

    def _parse_response(self, response: Any) -> AgentAction:
        """Parse OpenAI response into AgentAction."""
        # Track token usage
        if hasattr(response, "usage") and response.usage:
            self._total_input_tokens += getattr(response.usage, "prompt_tokens", 0)
            self._total_output_tokens += getattr(response.usage, "completion_tokens", 0)

        choice = response.choices[0]
        message = choice.message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function = tool_call.function

            full_name = function.name
            if "__" in full_name:
                tool_name, tool_action = full_name.split("__", 1)
            else:
                parts = full_name.rsplit("_", 1)
                if len(parts) == 2:
                    tool_name, tool_action = parts
                else:
                    tool_name = full_name
                    tool_action = "invoke"

            try:
                tool_args = json.loads(function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            return AgentAction(
                type="tool_call",
                tool_name=tool_name,
                tool_action=tool_action,
                tool_args=tool_args,
                tool_call_id=tool_call.id,
            )

        if choice.finish_reason == "stop" and not message.content:
            return AgentAction(type="stop")

        return AgentAction(
            type="message",
            content=message.content or "",
        )

    def get_usage(self) -> dict[str, int]:
        """Get accumulated token usage across all API calls.

        Returns:
            Dictionary with input_tokens and output_tokens counts.
        """
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
        }

    def reset_usage(self) -> None:
        """Reset token usage counters."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def _stub_response(self, history: list[Message]) -> AgentAction:
        """Return stub response when no API key is configured."""
        last_user = next(
            (m for m in reversed(history) if m.role == "user"),
            None,
        )

        if last_user:
            content = last_user.content.lower()
            if "refund" in content:
                return AgentAction(
                    type="message",
                    content=(
                        "I understand you're inquiring about a refund. "
                        "Let me look into that for you. Could you please "
                        "provide your order number?"
                    ),
                )
            if "order" in content:
                return AgentAction(
                    type="message",
                    content=(
                        "I'd be happy to help you with your order. "
                        "What would you like to know about it?"
                    ),
                )

        key_name = "OPENROUTER_API_KEY" if self._is_openrouter else "OPENAI_API_KEY"
        return AgentAction(
            type="message",
            content=(
                f"[STUB] No API key configured. "
                f"Set {key_name} environment variable to enable LLM calls."
            ),
        )
