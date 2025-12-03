"""LLM-based prompt agent using OpenAI SDK."""

import json
import os
from typing import Any

from sandboxy.agents.base import AgentAction, AgentConfig, BaseAgent
from sandboxy.core.state import Message


class LlmPromptAgent(BaseAgent):
    """Agent that uses an LLM via OpenAI-compatible API."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package required for LlmPromptAgent. "
                    "Install with: pip install openai"
                )
        return self._client

    def step(
        self,
        history: list[Message],
        available_tools: list[dict[str, Any]] | None = None,
    ) -> AgentAction:
        """Process conversation and return next action using LLM."""
        # If no API key, return stub response for development
        if not self.api_key:
            return self._stub_response(history)

        # Build messages for API call
        messages = self._build_messages(history)

        # Build tools if available
        tools = self._build_tools(available_tools) if available_tools else None

        try:
            response = self._call_api(messages, tools)
            return self._parse_response(response)
        except Exception as e:
            # Return error as message on failure
            return AgentAction(
                type="message",
                content=f"Error calling LLM: {e}",
            )

    def _build_messages(self, history: list[Message]) -> list[dict[str, Any]]:
        """Convert history to OpenAI message format."""
        messages: list[dict[str, Any]] = []

        # Add system prompt if configured
        if self.config.system_prompt:
            messages.append({
                "role": "system",
                "content": self.config.system_prompt,
            })

        # Convert history messages
        for msg in history:
            if msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id or msg.tool_name or "unknown",
                })
            elif msg.role == "assistant" and msg.tool_calls:
                # Assistant message with tool calls
                messages.append({
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
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return messages

    def _build_tools(
        self, available_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Build OpenAI tools format from available tools."""
        tools = []
        for tool in available_tools:
            # Each tool may have multiple actions
            actions = tool.get("actions", [])
            for action in actions:
                # Use double underscore to separate tool name from action
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{tool['name']}__{action['name']}",
                        "description": action.get("description", ""),
                        "parameters": action.get("parameters", {"type": "object", "properties": {}}),
                    },
                })
        return tools

    def _call_api(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        """Make API call to OpenAI."""
        model = self.config.model or "gpt-5-mini"
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        # Some models (like gpt-5-nano) don't support temperature
        # Only add it if not a nano model
        if "nano" not in model:
            kwargs["temperature"] = self.config.params.get("temperature", 0.2)

        # Modern OpenAI models use max_completion_tokens
        max_tokens = self.config.params.get("max_tokens", 1024)
        kwargs["max_completion_tokens"] = max_tokens

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)

    def _parse_response(self, response: Any) -> AgentAction:
        """Parse OpenAI response into AgentAction."""
        choice = response.choices[0]
        message = choice.message

        # Check for tool calls
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function = tool_call.function

            # Parse tool name and action from combined name (separated by __)
            full_name = function.name
            if "__" in full_name:
                tool_name, tool_action = full_name.split("__", 1)
            else:
                # Fallback for legacy single underscore format
                parts = full_name.rsplit("_", 1)
                if len(parts) == 2:
                    tool_name, tool_action = parts
                else:
                    tool_name = full_name
                    tool_action = "invoke"

            # Parse arguments
            try:
                tool_args = json.loads(function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            return AgentAction(
                type="tool_call",
                tool_name=tool_name,
                tool_action=tool_action,
                tool_args=tool_args,
            )

        # Check for stop
        if choice.finish_reason == "stop" and not message.content:
            return AgentAction(type="stop")

        # Return message content
        return AgentAction(
            type="message",
            content=message.content or "",
        )

    def _stub_response(self, history: list[Message]) -> AgentAction:
        """Return stub response when no API key is configured."""
        # Look at last user message to generate contextual stub
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
            elif "order" in content:
                return AgentAction(
                    type="message",
                    content=(
                        "I'd be happy to help you with your order. "
                        "What would you like to know about it?"
                    ),
                )

        return AgentAction(
            type="message",
            content=(
                "[STUB] This is a development stub response. "
                "Set OPENAI_API_KEY environment variable to enable real LLM calls."
            ),
        )
