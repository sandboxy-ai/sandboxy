"""Async Runner - executes MDL modules with support for interactive sessions.

This runner is designed for use with WebSocket connections where execution
can be paused to await user input.
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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

    def inject_event(
        self, tool_name: str, event_type: str, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Inject a game event by calling a tool's trigger_event action.

        This is used for chaos injection - frontend can trigger events like
        "heatwave" or "rush_hour" that modify the game state.

        Args:
            tool_name: Name of the tool to call (e.g., "stand" for lemonade stand).
            event_type: Type of event to trigger (e.g., "heatwave", "rush_hour").
            args: Optional additional arguments for the event.

        Returns:
            The tool result data.

        Raises:
            ValueError: If tool not found or event trigger fails.
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        tool = self.tools[tool_name]
        event_args = {"event": event_type}
        if args:
            event_args.update(args)

        result = tool.invoke("trigger_event", event_args, self.env_state)

        if not result.success:
            raise ValueError(f"Event trigger failed: {result.error}")

        return result.data or {}

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
                # If we've processed tool calls, the agent should respond based on results
                # Some models return empty content after tool calls - add a hint and retry once
                if tool_call_count > 0 and not hasattr(self, "_retry_after_tool"):
                    self._retry_after_tool = True
                    # Add a system hint to prompt the agent to respond
                    self.history.append(
                        Message(
                            role="user",
                            content="[System: Please respond to the customer based on the information you just retrieved.]",
                        )
                    )
                    continue  # Retry the loop

                # Clean up retry flag
                if hasattr(self, "_retry_after_tool"):
                    delattr(self, "_retry_after_tool")

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

        # Use the original tool_call_id from the model, or generate one as fallback
        tool_call_id = action.tool_call_id or f"call_{tool_name}_{tool_action}_{len(self.events)}"
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

        # Run all checks and collect results
        for check in self.module.evaluation:
            result = self._run_check(check)
            checks[check.name] = result

        # Compute final score based on scoring config
        score = self._compute_score(checks)

        return EvaluationResult(
            checks=checks,
            score=score,
            num_events=len(self.events),
            status="ok",
        )

    def _compute_score(self, checks: dict[str, Any]) -> float:
        """Compute final score based on scoring config.

        Supports three modes:
        1. Formula: Use a Python expression with check names as variables
        2. Weighted average: Average checks with optional weights
        3. Default: Simple average of all numeric/boolean results
        """
        scoring = self.module.scoring

        # Extract numeric values from checks for use in formulas
        check_values: dict[str, float] = {}
        for name, result in checks.items():
            if isinstance(result, int | float):
                check_values[name] = float(result)
            elif isinstance(result, bool):
                check_values[name] = 1.0 if result else 0.0
            elif isinstance(result, dict):
                if result.get("passed") is True:
                    check_values[name] = 1.0
                elif result.get("passed") is False:
                    check_values[name] = 0.0
                elif "value" in result and isinstance(result["value"], int | float):
                    check_values[name] = float(result["value"])

        # Mode 1: Custom formula
        if scoring.formula:
            try:
                score = self._eval_score_formula(scoring.formula, check_values)
            except Exception:
                # Fall back to weighted average on formula error
                score = self._weighted_average(check_values, scoring.weights)
        else:
            # Mode 2/3: Weighted average (with optional weights)
            score = self._weighted_average(check_values, scoring.weights)

        # Normalize if requested
        if scoring.normalize and scoring.max_score != scoring.min_score:
            score = (score - scoring.min_score) / (scoring.max_score - scoring.min_score)
            score = max(0.0, min(1.0, score))  # Clamp to 0-1

        return score

    def _eval_score_formula(self, formula: str, check_values: dict[str, float]) -> float:
        """Evaluate a score formula with check values as variables."""
        safe_builtins = {
            "True": True,
            "False": False,
            "None": None,
            "len": len,
            "min": min,
            "max": max,
            "abs": abs,
            "sum": sum,
            "round": round,
        }

        # Add env_state to context for formulas that reference it
        context = {"__builtins__": safe_builtins, "env_state": self.env_state}
        context.update(check_values)

        result = eval(formula, context, {})
        return float(result)

    def _weighted_average(self, values: dict[str, float], weights: dict[str, float]) -> float:
        """Compute weighted average of check values."""
        if not values:
            return 0.0

        total = 0.0
        total_weight = 0.0

        for name, value in values.items():
            weight = weights.get(name, 1.0)
            total += value * weight
            total_weight += weight

        return total / total_weight if total_weight > 0 else 0.0

    def _run_check(self, check: Any) -> dict[str, Any]:
        """Run a single evaluation check."""
        kind = check.kind

        try:
            if kind == "contains":
                return self._check_contains(check)
            if kind == "regex":
                return self._check_regex(check)
            if kind == "count":
                return self._check_count(check)
            if kind == "tool_called":
                return self._check_tool_called(check)
            if kind == "equals":
                return self._check_equals(check)
            if kind == "env_state":
                return self._check_env_state(check)
            if kind == "deterministic":
                # Legacy support for raw Python expressions
                return self._check_deterministic(check)
            if kind == "llm":
                return {"status": "skipped", "reason": "LLM eval not implemented"}
            return {"status": "error", "error": f"Unknown check kind: {kind}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_target_text(self, target: str) -> str:
        """Get text content for a target."""
        if target == "agent_messages":
            return " ".join(msg.content for msg in self.history if msg.role == "assistant")
        if target == "user_messages":
            return " ".join(msg.content for msg in self.history if msg.role == "user")
        if target == "all_messages":
            return " ".join(msg.content for msg in self.history)
        if target == "last_agent_message":
            for msg in reversed(self.history):
                if msg.role == "assistant":
                    return msg.content
            return ""
        if target == "last_user_message":
            for msg in reversed(self.history):
                if msg.role == "user":
                    return msg.content
            return ""
        return ""

    def _get_target_list(self, target: str) -> list[Any]:
        """Get list of items for a target."""
        if target == "agent_messages":
            return [msg for msg in self.history if msg.role == "assistant"]
        if target == "user_messages":
            return [msg for msg in self.history if msg.role == "user"]
        if target == "all_messages":
            return list(self.history)
        if target == "tool_calls":
            return [event for event in self.events if event.type == "tool_call"]
        return []

    def _check_contains(self, check: Any) -> dict[str, Any]:
        """Check if target contains a value."""
        target = check.target or "agent_messages"
        value = check.value or ""
        expected = check.expected
        case_sensitive = check.case_sensitive

        text = self._get_target_text(target)

        if not case_sensitive:
            text = text.lower()
            value = value.lower()

        found = value in text
        passed = found == expected

        return {
            "passed": passed,
            "found": found,
            "expected": expected,
            "searched_for": check.value,
            "in": target,
        }

    def _check_regex(self, check: Any) -> dict[str, Any]:
        """Check if target matches a regex pattern."""
        target = check.target or "agent_messages"
        pattern = check.pattern or ""
        expected = check.expected

        text = self._get_target_text(target)
        match = bool(re.search(pattern, text, re.IGNORECASE if not check.case_sensitive else 0))
        passed = match == expected

        return {
            "passed": passed,
            "matched": match,
            "expected": expected,
            "pattern": pattern,
            "in": target,
        }

    def _check_count(self, check: Any) -> dict[str, Any]:
        """Check count of items."""
        target = check.target or "agent_messages"
        min_count = check.min
        max_count = check.max

        items = self._get_target_list(target)
        count = len(items)

        passed = True
        if min_count is not None and count < min_count:
            passed = False
        if max_count is not None and count > max_count:
            passed = False

        return {
            "passed": passed,
            "count": count,
            "min": min_count,
            "max": max_count,
            "target": target,
        }

    def _check_tool_called(self, check: Any) -> dict[str, Any]:
        """Check if a specific tool was called."""
        tool_name = check.tool
        action_name = check.action
        expected = check.expected

        tool_calls = [e for e in self.events if e.type == "tool_call"]

        called = False
        for tc in tool_calls:
            payload = tc.payload
            if payload.get("tool") == tool_name:
                if action_name is None or payload.get("action") == action_name:
                    called = True
                    break

        passed = called == expected

        return {
            "passed": passed,
            "called": called,
            "expected": expected,
            "tool": tool_name,
            "action": action_name,
        }

    def _check_equals(self, check: Any) -> dict[str, Any]:
        """Check if a value equals expected."""
        target = check.target or ""
        expected_value = check.value

        # Handle env.* targets
        if target.startswith("env."):
            key = target[4:]
            actual_value = self.env_state.get(key)
        else:
            actual_value = self._get_target_text(target)

        passed = actual_value == expected_value

        return {
            "passed": passed,
            "actual": actual_value,
            "expected": expected_value,
            "target": target,
        }

    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get a nested value using dot notation (e.g., 'orders.ORD123.refunded')."""
        keys = path.split(".")
        current = obj
        for key in keys:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None
        return current

    def _check_env_state(self, check: Any) -> dict[str, Any]:
        """Check environment state value. Supports dot notation for nested access."""
        key = check.key or ""
        expected_value = check.value

        # Support dot notation for nested values (e.g., "orders.ORD123.refunded")
        if "." in key:
            actual_value = self._get_nested_value(self.env_state, key)
        else:
            actual_value = self.env_state.get(key)

        passed = actual_value == expected_value

        return {
            "passed": passed,
            "actual": actual_value,
            "expected": expected_value,
            "key": key,
        }

    def _check_deterministic(self, check: Any) -> dict[str, Any]:
        """Evaluate a deterministic check with Python expression and optional pass_if condition."""
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

            # Check for pass_if condition (e.g., ">=0", "<=5", ">=50")
            pass_if = check.config.get("pass_if")
            if pass_if and isinstance(result, int | float):
                passed = self._evaluate_pass_condition(result, pass_if)
                return {"passed": passed, "value": result, "condition": pass_if}
            if isinstance(result, bool):
                return {"passed": result}
            # For numeric values without pass_if, just return the value (no pass/fail)
            return {"value": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _evaluate_pass_condition(self, value: float, condition: str) -> bool:
        """Evaluate a pass_if condition like '>=0', '<=5', '>50'."""
        # Parse condition: operator + value (e.g., ">=50", "<=0", ">10")
        match = re.match(r"([<>=!]+)\s*(-?[\d.]+)", condition)
        if not match:
            return True  # No valid condition, default to pass

        op, threshold_str = match.groups()
        threshold = float(threshold_str)

        if op == ">=":
            return value >= threshold
        if op == "<=":
            return value <= threshold
        if op == ">":
            return value > threshold
        if op == "<":
            return value < threshold
        if op == "==" or op == "=":
            return value == threshold
        if op == "!=" or op == "<>":
            return value != threshold
        return True  # Unknown operator, default to pass

    def _safe_eval(self, expr: str, context: dict[str, Any]) -> Any:
        """Safely evaluate an expression with restricted scope (legacy support)."""
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
