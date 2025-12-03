"""Async Runner - executes MDL modules with support for interactive sessions.

This runner is designed for use with WebSocket connections where execution
can be paused to await user input.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, Field

from sandboxy.agents.base import Agent, AgentAction
from sandboxy.core.state import (
    EvaluationResult,
    Message,
    ModuleSpec,
    SessionState,
    Step,
    StepAction,
    ToolCall,
)
from sandboxy.tools.base import Tool, ToolResult
from sandboxy.tools.loader import ToolLoader


class RunEvent(BaseModel):
    """Event emitted during module execution."""

    type: str  # "user", "agent", "tool_call", "tool_result", "awaiting_input", "completed", "error"
    payload: dict[str, Any] = Field(default_factory=dict)


class AsyncRunner:
    """Executes MDL modules asynchronously with support for interactive sessions.

    This runner uses an async generator pattern to yield events and receive
    user input for `await_user` steps.

    Usage:
        runner = AsyncRunner(module, agent)
        async for event in runner.run():
            if event.type == "awaiting_input":
                # Get user input somehow
                user_input = await get_user_input()
                runner.provide_input(user_input)
            else:
                # Process other events
                handle_event(event)
    """

    def __init__(self, module: ModuleSpec, agent: Agent) -> None:
        """Initialize async runner.

        Args:
            module: MDL module specification to execute.
            agent: Agent to run within the module.
        """
        self.module = module
        self.agent = agent
        self.events: list[RunEvent] = []
        self.history: list[Message] = []
        self.env_state: dict[str, Any] = module.environment.initial_state.copy()
        self.tools: dict[str, Tool] = ToolLoader.from_env_config(module.environment)

        # Session state
        self.state = SessionState.IDLE
        self._user_input_future: asyncio.Future[str] | None = None
        self._step_index = 0

    @property
    def session_state(self) -> SessionState:
        """Get current session state."""
        return self.state

    def provide_input(self, content: str) -> None:
        """Provide user input for an await_user step.

        Args:
            content: User's input text.

        Raises:
            RuntimeError: If not currently awaiting user input.
        """
        if self._user_input_future is None or self._user_input_future.done():
            raise RuntimeError("Not currently awaiting user input")
        self._user_input_future.set_result(content)

    async def run(self) -> AsyncGenerator[RunEvent, None]:
        """Execute the module, yielding events as they occur.

        Yields:
            RunEvent objects for each significant event during execution.
            When type is "awaiting_input", caller should get user input
            and call provide_input() before continuing iteration.
        """
        self.state = SessionState.RUNNING
        steps = self.module.steps

        try:
            while self._step_index < len(steps):
                step = steps[self._step_index]

                if step.action == StepAction.INJECT_USER.value:
                    event = self._handle_inject_user(step)
                    self.events.append(event)
                    yield event

                elif step.action == StepAction.AWAIT_USER.value:
                    # Yield awaiting_input event and wait for user input
                    async for event in self._handle_await_user(step):
                        self.events.append(event)
                        yield event

                elif step.action == StepAction.AWAIT_AGENT.value:
                    self.state = SessionState.AWAITING_AGENT
                    async for event in self._handle_await_agent(step):
                        self.events.append(event)
                        yield event
                    self.state = SessionState.RUNNING

                elif step.action == StepAction.BRANCH.value:
                    event, new_steps = self._handle_branch(step)
                    if event:
                        self.events.append(event)
                        yield event
                    if new_steps is not None:
                        steps = new_steps
                        self._step_index = 0
                        continue

                elif step.action == StepAction.TOOL_CALL.value:
                    async for event in self._handle_direct_tool_call(step):
                        self.events.append(event)
                        yield event

                self._step_index += 1

            # Evaluation
            evaluation = self._evaluate()
            self.state = SessionState.COMPLETED

            yield RunEvent(
                type="completed",
                payload={
                    "evaluation": evaluation.model_dump(),
                    "num_events": len(self.events),
                },
            )

        except Exception as e:
            self.state = SessionState.ERROR
            yield RunEvent(
                type="error",
                payload={"message": str(e)},
            )

    def _handle_inject_user(self, step: Step) -> RunEvent:
        """Handle inject_user action - add scripted user message."""
        content = step.params.get("content", "")
        msg = Message(role="user", content=content)
        self.history.append(msg)

        return RunEvent(
            type="user",
            payload={"content": content, "step_id": step.id, "scripted": True},
        )

    async def _handle_await_user(self, step: Step) -> AsyncGenerator[RunEvent, None]:
        """Handle await_user action - wait for real user input."""
        prompt = step.params.get("prompt", "")
        timeout = step.params.get("timeout")

        self.state = SessionState.AWAITING_USER

        # Yield event to signal we're waiting for input
        yield RunEvent(
            type="awaiting_input",
            payload={"prompt": prompt, "step_id": step.id, "timeout": timeout},
        )

        # Create future for user input
        self._user_input_future = asyncio.get_event_loop().create_future()

        try:
            if timeout:
                content = await asyncio.wait_for(self._user_input_future, timeout=timeout)
            else:
                content = await self._user_input_future
        except TimeoutError:
            content = step.params.get("default", "[timeout - no input]")

        self._user_input_future = None
        self.state = SessionState.RUNNING

        # Add user message to history
        msg = Message(role="user", content=content)
        self.history.append(msg)

        yield RunEvent(
            type="user",
            payload={"content": content, "step_id": step.id, "scripted": False},
        )

    async def _handle_await_agent(
        self, step: Step, max_tool_calls: int = 10
    ) -> AsyncGenerator[RunEvent, None]:
        """Handle await_agent action - get agent response.

        May involve multiple tool calls before agent returns a message.
        """
        tool_call_count = 0

        while tool_call_count < max_tool_calls:
            # Build tool schemas for agent
            tool_schemas = self._get_tool_schemas()

            # Get agent action (this could be made async if agent supports it)
            action: AgentAction = self.agent.step(self.history, tool_schemas)

            if action.type == "message":
                msg = Message(role="assistant", content=action.content or "")
                self.history.append(msg)

                yield RunEvent(
                    type="agent",
                    payload={"content": msg.content, "step_id": step.id},
                )
                return  # Done with this await_agent step

            elif action.type == "tool_call":
                async for event in self._handle_tool_call(action, step):
                    yield event
                tool_call_count += 1
                # Continue loop to let agent respond to tool result

            elif action.type == "stop":
                yield RunEvent(
                    type="agent_stop",
                    payload={"step_id": step.id},
                )
                return

    async def _handle_tool_call(
        self, action: AgentAction, step: Step
    ) -> AsyncGenerator[RunEvent, None]:
        """Handle a tool call from the agent."""
        tool_name = action.tool_name or ""
        tool_action = action.tool_action or ""
        tool_args = action.tool_args or {}

        # Generate unique tool call ID
        tool_call_id = f"call_{tool_name}_{tool_action}_{len(self.events)}"
        function_name = f"{tool_name}__{tool_action}"

        yield RunEvent(
            type="tool_call",
            payload={
                "tool": tool_name,
                "action": tool_action,
                "args": tool_args,
                "step_id": step.id,
            },
        )

        # Add assistant message with tool_calls
        self.history.append(
            Message(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(
                        id=tool_call_id,
                        name=function_name,
                        arguments=json.dumps(tool_args),
                    )
                ],
            )
        )

        # Execute tool
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result: ToolResult = tool.invoke(tool_action, tool_args, self.env_state)

            yield RunEvent(
                type="tool_result",
                payload={
                    "tool": tool_name,
                    "action": tool_action,
                    "result": result.model_dump(),
                },
            )

            # Add tool result to history
            self.history.append(
                Message(
                    role="tool",
                    content=json.dumps(result.data) if result.success else result.error or "",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )
        else:
            error_msg = f"Tool not found: {tool_name}"
            yield RunEvent(
                type="tool_result",
                payload={
                    "tool": tool_name,
                    "action": tool_action,
                    "result": {"success": False, "error": error_msg},
                },
            )
            self.history.append(
                Message(
                    role="tool",
                    content=error_msg,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )

    async def _handle_direct_tool_call(self, step: Step) -> AsyncGenerator[RunEvent, None]:
        """Handle direct tool_call action (not via agent)."""
        tool_name = step.params.get("tool", "")
        tool_action = step.params.get("action", "")
        tool_args = step.params.get("args", {})

        yield RunEvent(
            type="tool_call",
            payload={
                "tool": tool_name,
                "action": tool_action,
                "args": tool_args,
                "step_id": step.id,
                "direct": True,
            },
        )

        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result: ToolResult = tool.invoke(tool_action, tool_args, self.env_state)

            yield RunEvent(
                type="tool_result",
                payload={
                    "tool": tool_name,
                    "action": tool_action,
                    "result": result.model_dump(),
                },
            )
        else:
            yield RunEvent(
                type="tool_result",
                payload={
                    "tool": tool_name,
                    "action": tool_action,
                    "result": {"success": False, "error": f"Tool not found: {tool_name}"},
                },
            )

    def _handle_branch(self, step: Step) -> tuple[RunEvent | None, list[Step] | None]:
        """Handle branch action."""
        branch_name = step.params.get("branch_name")

        event = RunEvent(
            type="branch",
            payload={"branch": branch_name, "step_id": step.id},
        )

        if branch_name and branch_name in self.module.branches:
            return event, self.module.branches[branch_name]

        return event, None

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for agent tool calling."""
        schemas = []
        for name, tool in self.tools.items():
            schemas.append(
                {
                    "name": name,
                    "description": tool.description,
                    "actions": tool.get_actions(),
                }
            )
        return schemas

    def _evaluate(self) -> EvaluationResult:
        """Run evaluation checks and compute score."""
        checks: dict[str, Any] = {}
        total_score = 0.0
        num_checks = 0

        for check in self.module.evaluation:
            if check.kind == "deterministic":
                result = self._eval_deterministic(check)
                checks[check.name] = result
                if isinstance(result, (int, float)):
                    total_score += result
                    num_checks += 1
                elif isinstance(result, bool):
                    total_score += 1.0 if result else 0.0
                    num_checks += 1
            elif check.kind == "llm":
                checks[check.name] = {"status": "skipped", "reason": "LLM eval not implemented"}

        score = total_score / num_checks if num_checks > 0 else 0.0

        return EvaluationResult(
            checks=checks,
            score=score,
            num_events=len(self.events),
            status="ok",
        )

    def _eval_deterministic(self, check: Any) -> Any:
        """Evaluate a deterministic check."""
        expr = check.config.get("expr", "")
        if not expr or expr == "TODO":
            return {"status": "skipped", "reason": "No expression defined"}

        context = {
            "env_state": self.env_state,
            "history": [msg.model_dump() for msg in self.history],
            "events": [event.model_dump() for event in self.events],
        }

        try:
            result = self._safe_eval(expr, context)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _safe_eval(self, expr: str, context: dict[str, Any]) -> Any:
        """Safely evaluate an expression with restricted scope."""
        safe_builtins = {
            "True": True,
            "False": False,
            "None": None,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "any": any,
            "all": all,
        }

        safe_globals = {"__builtins__": safe_builtins}
        safe_globals.update(context)

        return eval(expr, safe_globals, {})
