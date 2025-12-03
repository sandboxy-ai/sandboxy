"""Runner - executes MDL modules with agents and tools."""

import json
from typing import Any

from pydantic import BaseModel, Field

from sandboxy.agents.base import Agent, AgentAction
from sandboxy.core.state import EvaluationResult, Message, ModuleSpec, Step, ToolCall
from sandboxy.tools.base import Tool, ToolResult
from sandboxy.tools.loader import ToolLoader


class RunEvent(BaseModel):
    """Event recorded during module execution."""

    type: str  # "user", "agent", "tool_call", "tool_result", "branch", "eval"
    payload: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Result of running a module with an agent."""

    module_id: str
    agent_id: str
    events: list[RunEvent] = Field(default_factory=list)
    evaluation: EvaluationResult = Field(default_factory=EvaluationResult)

    def to_json(self, indent: int | None = None) -> str:
        """Serialize result to JSON string."""
        return self.model_dump_json(indent=indent)

    def pretty(self) -> str:
        """Format result for human-readable display."""
        lines = [
            f"Module: {self.module_id}",
            f"Agent: {self.agent_id}",
            "",
        ]

        for event in self.events:
            if event.type == "user":
                lines.append(f"USER: {event.payload.get('content', '')}")
            elif event.type == "agent":
                lines.append(f"AGENT: {event.payload.get('content', '')}")
            elif event.type == "tool_call":
                tool = event.payload.get("tool", "")
                action = event.payload.get("action", "")
                args = event.payload.get("args", {})
                lines.append(f"TOOL CALL: {tool}.{action}({args})")
            elif event.type == "tool_result":
                result = event.payload.get("result", {})
                success = result.get("success", False)
                data = result.get("data", "")
                status = "OK" if success else "FAIL"
                lines.append(f"TOOL RESULT [{status}]: {data}")
            elif event.type == "branch":
                branch = event.payload.get("branch", "")
                lines.append(f"[BRANCH] → {branch}")

        lines.append("")
        lines.append("EVALUATION:")
        lines.append(f"  Score: {self.evaluation.score}")
        lines.append(f"  Status: {self.evaluation.status}")
        lines.append(f"  Events: {self.evaluation.num_events}")
        if self.evaluation.checks:
            lines.append(f"  Checks: {json.dumps(self.evaluation.checks, indent=2)}")

        return "\n".join(lines)


class Runner:
    """Executes MDL modules with agents and tools."""

    def __init__(self, module: ModuleSpec, agent: Agent) -> None:
        """Initialize runner with module and agent.

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

    def run(self) -> RunResult:
        """Execute the module and return results.

        Returns:
            Result containing events and evaluation.
        """
        step_index = 0
        steps = self.module.steps

        while step_index < len(steps):
            step = steps[step_index]
            next_index = step_index + 1

            if step.action == "inject_user":
                self._handle_inject_user(step)

            elif step.action == "await_agent":
                should_stop = self._handle_await_agent(step)
                if should_stop:
                    break

            elif step.action == "branch":
                new_steps, new_index = self._handle_branch(step)
                if new_steps is not None:
                    steps = new_steps
                    step_index = new_index
                    continue

            step_index = next_index

        evaluation = self._evaluate()
        return RunResult(
            module_id=self.module.id,
            agent_id=self.agent.config.id,
            events=self.events,
            evaluation=evaluation,
        )

    def _handle_inject_user(self, step: Step) -> None:
        """Handle inject_user action - add user message to history."""
        content = step.params.get("content", "")
        msg = Message(role="user", content=content)
        self.history.append(msg)
        self.events.append(
            RunEvent(
                type="user",
                payload={"content": content, "step_id": step.id},
            )
        )

    def _handle_await_agent(self, step: Step, max_tool_calls: int = 10) -> bool:
        """Handle await_agent action - get agent response.

        The agent may make multiple tool calls before responding with a message.
        We loop until the agent returns a message or stop action.

        Args:
            step: Current step being executed.
            max_tool_calls: Maximum tool calls allowed before forcing stop.

        Returns:
            True if agent wants to stop, False otherwise.
        """
        tool_call_count = 0

        while tool_call_count < max_tool_calls:
            # Build tool schemas for agent
            tool_schemas = self._get_tool_schemas()

            # Get agent action
            action: AgentAction = self.agent.step(self.history, tool_schemas)

            if action.type == "message":
                msg = Message(role="assistant", content=action.content or "")
                self.history.append(msg)
                self.events.append(
                    RunEvent(
                        type="agent",
                        payload={"content": msg.content, "step_id": step.id},
                    )
                )
                return False  # Done with this await_agent step

            elif action.type == "tool_call":
                self._handle_tool_call(action, step)
                tool_call_count += 1
                # Continue loop to let agent respond to tool result

            elif action.type == "stop":
                return True

        # Max tool calls reached
        return False

    def _handle_tool_call(self, action: AgentAction, step: Step) -> None:
        """Handle a tool call from the agent."""
        tool_name = action.tool_name or ""
        tool_action = action.tool_action or ""
        tool_args = action.tool_args or {}

        # Generate unique tool call ID
        tool_call_id = f"call_{tool_name}_{tool_action}_{len(self.events)}"
        # Function name uses double underscore separator (matching _build_tools)
        function_name = f"{tool_name}__{tool_action}"

        self.events.append(
            RunEvent(
                type="tool_call",
                payload={
                    "tool": tool_name,
                    "action": tool_action,
                    "args": tool_args,
                    "step_id": step.id,
                },
            )
        )

        # Add assistant message with tool_calls BEFORE the tool result
        # This is required by OpenAI API
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

        # Execute tool if available
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result: ToolResult = tool.invoke(tool_action, tool_args, self.env_state)

            self.events.append(
                RunEvent(
                    type="tool_result",
                    payload={
                        "tool": tool_name,
                        "action": tool_action,
                        "result": result.model_dump(),
                    },
                )
            )

            # Add tool result to history with matching tool_call_id
            self.history.append(
                Message(
                    role="tool",
                    content=json.dumps(result.data) if result.success else result.error or "",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )
        else:
            # Tool not found - still add tool result message
            error_msg = f"Tool not found: {tool_name}"
            self.events.append(
                RunEvent(
                    type="tool_result",
                    payload={
                        "tool": tool_name,
                        "action": tool_action,
                        "result": {"success": False, "error": error_msg},
                    },
                )
            )
            self.history.append(
                Message(
                    role="tool",
                    content=error_msg,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )

    def _handle_branch(self, step: Step) -> tuple[list[Step] | None, int]:
        """Handle branch action.

        Returns:
            Tuple of (new_steps, new_index) if branching, (None, 0) otherwise.
        """
        branch_name = step.params.get("branch_name")

        self.events.append(
            RunEvent(
                type="branch",
                payload={"branch": branch_name, "step_id": step.id},
            )
        )

        if branch_name and branch_name in self.module.branches:
            return self.module.branches[branch_name], 0

        return None, 0

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for agent tool calling."""
        schemas = []
        for name, tool in self.tools.items():
            schemas.append({
                "name": name,
                "description": tool.description,
                "actions": tool.get_actions(),
            })
        return schemas

    def _evaluate(self) -> EvaluationResult:
        """Run evaluation checks and compute score.

        Returns:
            Evaluation result with checks and score.
        """
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
                # LLM evaluation not implemented in MVP
                checks[check.name] = {"status": "skipped", "reason": "LLM eval not implemented"}

        # Compute average score if we have checks
        score = total_score / num_checks if num_checks > 0 else 0.0

        return EvaluationResult(
            checks=checks,
            score=score,
            num_events=len(self.events),
            status="ok",
        )

    def _eval_deterministic(self, check: Any) -> Any:
        """Evaluate a deterministic check.

        Args:
            check: Evaluation check with expr in config.

        Returns:
            Result of evaluation (bool, number, or error dict).
        """
        expr = check.config.get("expr", "")
        if not expr or expr == "TODO":
            return {"status": "skipped", "reason": "No expression defined"}

        # Build evaluation context
        context = {
            "env_state": self.env_state,
            "history": [msg.model_dump() for msg in self.history],
            "events": [event.model_dump() for event in self.events],
        }

        try:
            # Safe evaluation using restricted builtins
            result = self._safe_eval(expr, context)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _safe_eval(self, expr: str, context: dict[str, Any]) -> Any:
        """Safely evaluate an expression with restricted scope.

        Args:
            expr: Expression to evaluate.
            context: Variables available in expression.

        Returns:
            Result of evaluation.
        """
        # Restrict available builtins
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

        # Create restricted globals
        safe_globals = {"__builtins__": safe_builtins}
        safe_globals.update(context)

        return eval(expr, safe_globals, {})
