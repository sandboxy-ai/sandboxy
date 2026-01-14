"""Factory classes for creating test objects with sensible defaults.

This module provides factory classes that make it easy to create test objects
with default values, while allowing customization of specific fields.

Usage:
    # Create with defaults
    config = AgentConfigFactory.create()

    # Create with custom values
    config = AgentConfigFactory.create(model="gpt-5", system_prompt="Custom prompt")

    # Use helper methods
    module = ModuleSpecFactory.with_evaluation()
    module = ModuleSpecFactory.with_branches()
"""

import uuid
from typing import Any

from sandboxy.agents.base import AgentAction, AgentConfig
from sandboxy.core.state import (
    EnvConfig,
    EvaluationCheck,
    Message,
    ModuleSpec,
    ScoringConfig,
    Step,
    ToolRef,
)
from sandboxy.tools.base import ToolConfig, ToolResult


class AgentConfigFactory:
    """Factory for AgentConfig objects."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        name: str | None = None,
        kind: str = "llm-prompt",
        model: str = "gpt-4o",
        system_prompt: str = "You are a helpful assistant.",
        tools: list[str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> AgentConfig:
        """Create an AgentConfig with sensible defaults.

        Args:
            id: Agent ID (auto-generated if None)
            name: Display name (auto-generated if None)
            kind: Agent kind (default: "llm-prompt")
            model: Model ID (default: "gpt-4o")
            system_prompt: System prompt text
            tools: List of tool names
            params: Additional parameters

        Returns:
            AgentConfig instance

        """
        cls._counter += 1
        return AgentConfig(
            id=id or f"test/agent-{cls._counter}",
            name=name or f"Test Agent {cls._counter}",
            kind=kind,
            model=model,
            system_prompt=system_prompt,
            tools=tools or [],
            params=params or {},
        )

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the counter (useful for test isolation)."""
        cls._counter = 0


class ModuleSpecFactory:
    """Factory for ModuleSpec objects."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        description: str = "Test module",
        tools: list[ToolRef] | None = None,
        initial_state: dict[str, Any] | None = None,
        steps: list[Step] | None = None,
        evaluation: list[EvaluationCheck] | None = None,
        scoring: ScoringConfig | None = None,
        branches: dict[str, list[Step]] | None = None,
    ) -> ModuleSpec:
        """Create a ModuleSpec with sensible defaults.

        Args:
            id: Module ID (auto-generated if None)
            description: Module description
            tools: List of tool references
            initial_state: Initial environment state
            steps: Execution steps (default: inject_user + await_agent)
            evaluation: Evaluation checks
            scoring: Scoring configuration
            branches: Named branch definitions

        Returns:
            ModuleSpec instance

        """
        cls._counter += 1

        default_steps = [
            Step(id="s1", action="inject_user", params={"content": "Test message"}),
            Step(id="s2", action="await_agent", params={}),
        ]

        return ModuleSpec(
            id=id or f"test/module-{cls._counter}",
            description=description,
            environment=EnvConfig(
                sandbox_type="local",
                tools=tools or [],
                initial_state=initial_state or {},
            ),
            steps=steps or default_steps,
            evaluation=evaluation or [],
            scoring=scoring or ScoringConfig(),
            branches=branches or {},
        )

    @classmethod
    def with_evaluation(
        cls,
        checks: list[EvaluationCheck] | None = None,
        **kwargs: Any,
    ) -> ModuleSpec:
        """Create a module with evaluation checks.

        Args:
            checks: Custom evaluation checks (uses defaults if None)
            **kwargs: Additional arguments passed to create()

        Returns:
            ModuleSpec with evaluation

        """
        default_checks = [
            EvaluationCheck(
                name="ResponseCheck",
                kind="contains",
                target="agent_messages",
                value="help",
                expected=True,
            ),
        ]
        return cls.create(evaluation=checks or default_checks, **kwargs)

    @classmethod
    def with_branches(
        cls,
        branch_name: str = "alternate",
        branch_steps: list[Step] | None = None,
        **kwargs: Any,
    ) -> ModuleSpec:
        """Create a module with branch definitions.

        Args:
            branch_name: Name of the branch
            branch_steps: Steps in the branch
            **kwargs: Additional arguments passed to create()

        Returns:
            ModuleSpec with branches

        """
        default_branch_steps = [
            Step(id="b1", action="inject_user", params={"content": "Branch message"}),
            Step(id="b2", action="await_agent", params={}),
        ]
        branches = {branch_name: branch_steps or default_branch_steps}
        return cls.create(branches=branches, **kwargs)

    @classmethod
    def with_tool(
        cls,
        tool_name: str = "test_tool",
        tool_type: str = "mock_test",
        initial_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModuleSpec:
        """Create a module with a mock tool.

        Args:
            tool_name: Name of the tool
            tool_type: Type of the tool
            initial_state: Initial environment state
            **kwargs: Additional arguments passed to create()

        Returns:
            ModuleSpec with a tool configured

        """
        tools = [ToolRef(name=tool_name, type=tool_type)]
        return cls.create(tools=tools, initial_state=initial_state or {}, **kwargs)

    @classmethod
    def with_shopify_tool(
        cls,
        initial_balance: float = 1000.0,
        **kwargs: Any,
    ) -> ModuleSpec:
        """Create a module with a mock shopify tool.

        This is a convenience method for tests that need a tool that
        simulates an e-commerce backend.

        Args:
            initial_balance: Initial cash balance in the state
            **kwargs: Additional arguments passed to create()

        Returns:
            ModuleSpec with shopify tool configured

        """
        tools = [ToolRef(name="shopify", type="mock_test", description="Mock store tool")]
        initial_state = {"cash_balance": initial_balance}
        return cls.create(tools=tools, initial_state=initial_state, **kwargs)

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the counter (useful for test isolation)."""
        cls._counter = 0


class AgentActionFactory:
    """Factory for AgentAction objects."""

    @classmethod
    def message(cls, content: str = "Test response") -> AgentAction:
        """Create a message action.

        Args:
            content: Message content

        Returns:
            AgentAction with type="message"

        """
        return AgentAction(type="message", content=content)

    @classmethod
    def tool_call(
        cls,
        tool_name: str = "test_tool",
        action: str = "test_action",
        args: dict[str, Any] | None = None,
        tool_call_id: str | None = None,
    ) -> AgentAction:
        """Create a tool call action.

        Args:
            tool_name: Name of the tool
            action: Action to perform on the tool
            args: Arguments for the action
            tool_call_id: Tool call ID (auto-generated if None)

        Returns:
            AgentAction with type="tool_call"

        """
        return AgentAction(
            type="tool_call",
            tool_name=tool_name,
            tool_action=action,
            tool_args=args or {},
            tool_call_id=tool_call_id or uuid.uuid4().hex[:9],
        )

    @classmethod
    def stop(cls) -> AgentAction:
        """Create a stop action.

        Returns:
            AgentAction with type="stop"

        """
        return AgentAction(type="stop")


class MessageFactory:
    """Factory for Message objects."""

    @classmethod
    def user(cls, content: str = "Test user message") -> Message:
        """Create a user message.

        Args:
            content: Message content

        Returns:
            Message with role="user"

        """
        return Message(role="user", content=content)

    @classmethod
    def assistant(cls, content: str = "Test assistant message") -> Message:
        """Create an assistant message.

        Args:
            content: Message content

        Returns:
            Message with role="assistant"

        """
        return Message(role="assistant", content=content)

    @classmethod
    def tool(
        cls,
        content: str = '{"result": "success"}',
        tool_name: str = "test_tool",
        tool_call_id: str | None = None,
    ) -> Message:
        """Create a tool result message.

        Args:
            content: Tool result content (usually JSON)
            tool_name: Name of the tool that was called
            tool_call_id: ID of the original tool call

        Returns:
            Message with role="tool"

        """
        return Message(
            role="tool",
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id or f"call_{uuid.uuid4().hex[:8]}",
        )

    @classmethod
    def system(cls, content: str = "System message") -> Message:
        """Create a system message.

        Args:
            content: Message content

        Returns:
            Message with role="system"

        """
        return Message(role="system", content=content)

    @classmethod
    def conversation(cls, turns: int = 3) -> list[Message]:
        """Create a multi-turn conversation.

        Args:
            turns: Number of conversation turns (user + assistant pairs)

        Returns:
            List of alternating user/assistant messages

        """
        messages = []
        for i in range(turns):
            messages.append(cls.user(f"User message {i + 1}"))
            messages.append(cls.assistant(f"Assistant response {i + 1}"))
        return messages


class ToolConfigFactory:
    """Factory for ToolConfig objects."""

    _counter = 0

    @classmethod
    def create(
        cls,
        name: str | None = None,
        type: str = "mock_test",
        description: str = "Test tool",
        config: dict[str, Any] | None = None,
    ) -> ToolConfig:
        """Create a ToolConfig with sensible defaults.

        Args:
            name: Tool name (auto-generated if None)
            type: Tool type
            description: Tool description
            config: Tool configuration

        Returns:
            ToolConfig instance

        """
        cls._counter += 1
        return ToolConfig(
            name=name or f"tool_{cls._counter}",
            type=type,
            description=description,
            config=config or {},
        )

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the counter (useful for test isolation)."""
        cls._counter = 0


class ToolResultFactory:
    """Factory for ToolResult objects."""

    @classmethod
    def success(cls, data: dict[str, Any] | None = None) -> ToolResult:
        """Create a successful tool result.

        Args:
            data: Result data

        Returns:
            ToolResult with success=True

        """
        return ToolResult(success=True, data=data or {"status": "ok"})

    @classmethod
    def error(cls, message: str = "Operation failed") -> ToolResult:
        """Create a failed tool result.

        Args:
            message: Error message

        Returns:
            ToolResult with success=False

        """
        return ToolResult(success=False, error=message)


class StepFactory:
    """Factory for Step objects."""

    _counter = 0

    @classmethod
    def inject_user(cls, content: str = "Test message", id: str | None = None) -> Step:
        """Create an inject_user step.

        Args:
            content: User message content
            id: Step ID (auto-generated if None)

        Returns:
            Step with action="inject_user"

        """
        cls._counter += 1
        return Step(
            id=id or f"s{cls._counter}",
            action="inject_user",
            params={"content": content},
        )

    @classmethod
    def await_agent(cls, id: str | None = None) -> Step:
        """Create an await_agent step.

        Args:
            id: Step ID (auto-generated if None)

        Returns:
            Step with action="await_agent"

        """
        cls._counter += 1
        return Step(
            id=id or f"s{cls._counter}",
            action="await_agent",
            params={},
        )

    @classmethod
    def await_user(
        cls,
        prompt: str = "Enter input:",
        timeout: int | None = None,
        id: str | None = None,
    ) -> Step:
        """Create an await_user step.

        Args:
            prompt: Prompt to show user
            timeout: Timeout in seconds
            id: Step ID (auto-generated if None)

        Returns:
            Step with action="await_user"

        """
        cls._counter += 1
        params: dict[str, Any] = {"prompt": prompt}
        if timeout is not None:
            params["timeout"] = timeout
        return Step(
            id=id or f"s{cls._counter}",
            action="await_user",
            params=params,
        )

    @classmethod
    def branch(cls, branch_name: str, id: str | None = None) -> Step:
        """Create a branch step.

        Args:
            branch_name: Name of the branch to jump to
            id: Step ID (auto-generated if None)

        Returns:
            Step with action="branch"

        """
        cls._counter += 1
        return Step(
            id=id or f"s{cls._counter}",
            action="branch",
            params={"branch_name": branch_name},
        )

    @classmethod
    def tool_call(
        cls,
        tool: str,
        action: str,
        args: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> Step:
        """Create a direct tool_call step.

        Args:
            tool: Tool name
            action: Action to perform
            args: Arguments for the action
            id: Step ID (auto-generated if None)

        Returns:
            Step with action="tool_call"

        """
        cls._counter += 1
        return Step(
            id=id or f"s{cls._counter}",
            action="tool_call",
            params={"tool": tool, "action": action, "args": args or {}},
        )

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the counter (useful for test isolation)."""
        cls._counter = 0


class EvaluationCheckFactory:
    """Factory for EvaluationCheck objects."""

    @classmethod
    def contains(
        cls,
        name: str = "ContainsCheck",
        value: str = "expected",
        target: str = "agent_messages",
        expected: bool = True,
        case_sensitive: bool = False,
    ) -> EvaluationCheck:
        """Create a contains check.

        Args:
            name: Check name
            value: String to look for
            target: What to search in
            expected: True if should contain, False if should not
            case_sensitive: Whether to do case-sensitive match

        Returns:
            EvaluationCheck with kind="contains"

        """
        return EvaluationCheck(
            name=name,
            kind="contains",
            target=target,
            value=value,
            expected=expected,
            case_sensitive=case_sensitive,
        )

    @classmethod
    def regex(
        cls,
        name: str = "RegexCheck",
        pattern: str = r".*",
        target: str = "agent_messages",
        expected: bool = True,
    ) -> EvaluationCheck:
        """Create a regex check.

        Args:
            name: Check name
            pattern: Regex pattern
            target: What to search in
            expected: True if should match, False if should not

        Returns:
            EvaluationCheck with kind="regex"

        """
        return EvaluationCheck(
            name=name,
            kind="regex",
            target=target,
            pattern=pattern,
            expected=expected,
        )

    @classmethod
    def tool_called(
        cls,
        name: str = "ToolCalledCheck",
        tool: str = "test_tool",
        action: str | None = None,
        expected: bool = True,
    ) -> EvaluationCheck:
        """Create a tool_called check.

        Args:
            name: Check name
            tool: Tool name to check for
            action: Specific action to check for (optional)
            expected: True if should be called, False if should not

        Returns:
            EvaluationCheck with kind="tool_called"

        """
        return EvaluationCheck(
            name=name,
            kind="tool_called",
            tool=tool,
            action=action,
            expected=expected,
        )

    @classmethod
    def env_state(
        cls,
        name: str = "EnvStateCheck",
        key: str = "status",
        value: Any = "ok",
    ) -> EvaluationCheck:
        """Create an env_state check.

        Args:
            name: Check name
            key: State key to check
            value: Expected value

        Returns:
            EvaluationCheck with kind="env_state"

        """
        return EvaluationCheck(
            name=name,
            kind="env_state",
            key=key,
            value=value,
        )

    @classmethod
    def count(
        cls,
        name: str = "CountCheck",
        target: str = "agent_messages",
        min: int | None = None,
        max: int | None = None,
    ) -> EvaluationCheck:
        """Create a count check.

        Args:
            name: Check name
            target: What to count
            min: Minimum count
            max: Maximum count

        Returns:
            EvaluationCheck with kind="count"

        """
        return EvaluationCheck(
            name=name,
            kind="count",
            target=target,
            min=min,
            max=max,
        )
