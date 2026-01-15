"""Scenario runner - execute scenarios with YAML-defined and MCP tools."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from sandboxy.agents.base import Agent, AgentAction
from sandboxy.scenarios.loader import ScenarioSpec, StepSpec
from sandboxy.tools.base import ToolResult
from sandboxy.tools.loader import YAML_TOOL_DIRS
from sandboxy.tools.yaml_tools import load_scenario_tools

logger = logging.getLogger(__name__)


class ScenarioEvent(BaseModel):
    """Event recorded during scenario execution."""

    type: str  # "user", "agent", "tool_call", "tool_result", "system"
    payload: dict[str, Any] = Field(default_factory=dict)


class ScenarioResult(BaseModel):
    """Result of running a scenario."""

    scenario_id: str
    agent_id: str
    events: list[ScenarioEvent] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    final_state: dict[str, Any] = Field(default_factory=dict)
    goals_achieved: list[str] = Field(default_factory=list)
    score: float = 0.0

    def to_json(self, indent: int | None = None) -> str:
        """Serialize result to JSON string."""
        return self.model_dump_json(indent=indent)

    def pretty(self) -> str:
        """Format result for human-readable display."""
        lines = [
            f"Scenario: {self.scenario_id}",
            f"Agent: {self.agent_id}",
            "",
        ]

        for event in self.events:
            if event.type == "user":
                lines.append(f"USER: {event.payload.get('content', '')[:100]}...")
            elif event.type == "agent":
                content = event.payload.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                lines.append(f"AGENT: {content}")
            elif event.type == "tool_call":
                tool = event.payload.get("tool", "")
                action = event.payload.get("action", "")
                lines.append(f"TOOL: {tool}.{action}()")
            elif event.type == "tool_result":
                success = event.payload.get("success", False)
                status = "OK" if success else "FAIL"
                data = str(event.payload.get("data", ""))[:50]
                lines.append(f"  -> [{status}] {data}")

        lines.append("")
        lines.append(f"Tool Calls Made: {len(self.tool_calls)}")
        lines.append(f"Goals Achieved: {len(self.goals_achieved)}")
        lines.append(f"Score: {self.score}")

        return "\n".join(lines)


class Message(BaseModel):
    """A message in conversation history."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ScenarioRunner:
    """Runs scenarios with YAML-defined and MCP tools."""

    def __init__(
        self,
        scenario: ScenarioSpec,
        agent: Agent,
        tool_dirs: list[Path] | None = None,
    ) -> None:
        """Initialize the scenario runner.

        Args:
            scenario: The scenario specification
            agent: The agent to run
            tool_dirs: Optional directories to search for tool libraries
        """
        self.scenario = scenario
        self.agent = agent
        self.tool_dirs = tool_dirs or YAML_TOOL_DIRS

        # Load YAML tools
        scenario_data = {
            "tools_from": scenario.tools_from,
            "tools": scenario.tools,
        }
        self.tools: dict[str, Any] = load_scenario_tools(scenario_data, self.tool_dirs)
        self._mcp_tools: dict[str, Any] = {}  # MCP tools loaded separately
        self._mcp_manager: Any = None

        # Initialize state
        self.env_state: dict[str, Any] = scenario.initial_state.copy()
        self.history: list[Message] = []
        self.events: list[ScenarioEvent] = []
        self.tool_call_log: list[dict[str, Any]] = []

    async def _load_mcp_tools(self) -> None:
        """Load MCP tools from configured servers."""
        if not self.scenario.mcp_servers:
            return

        from sandboxy.mcp.client import McpManager, McpServerConfig

        self._mcp_manager = McpManager()

        configs = [
            McpServerConfig(
                name=server.name,
                # Local (stdio) transport
                command=server.command,
                args=server.args,
                env=server.env,
                # Remote (HTTP) transport
                url=server.url,
                headers=server.headers,
                transport=server.transport,  # type: ignore[arg-type]
            )
            for server in self.scenario.mcp_servers
        ]

        self._mcp_tools = await self._mcp_manager.connect_all(configs)

        # Merge MCP tools with YAML tools (YAML tools take precedence)
        for name, tool in self._mcp_tools.items():
            if name not in self.tools:
                self.tools[name] = tool

    async def _cleanup_mcp(self) -> None:
        """Disconnect from MCP servers."""
        if self._mcp_manager:
            await self._mcp_manager.disconnect_all()

    def run(self, max_turns: int = 20) -> ScenarioResult:
        """Execute the scenario synchronously.

        Args:
            max_turns: Maximum number of conversation turns

        Returns:
            ScenarioResult with events and evaluation
        """
        return asyncio.run(self.run_async(max_turns))

    async def run_async(self, max_turns: int = 20) -> ScenarioResult:
        """Execute the scenario asynchronously.

        Args:
            max_turns: Maximum number of conversation turns

        Returns:
            ScenarioResult with events and evaluation
        """
        try:
            # Load MCP tools if configured
            await self._load_mcp_tools()

            # Add system prompt to history
            if self.scenario.system_prompt:
                self.history.append(Message(role="system", content=self.scenario.system_prompt))

            # Execute steps
            for step in self.scenario.steps:
                await self._execute_step(step, max_turns)

            # Evaluate goals
            goals_achieved = self._evaluate_goals()
            score = self._compute_score(goals_achieved)

            return ScenarioResult(
                scenario_id=self.scenario.id,
                agent_id=self.agent.config.id,
                events=self.events,
                tool_calls=self.tool_call_log,
                final_state=self.env_state.copy(),
                goals_achieved=goals_achieved,
                score=score,
            )
        finally:
            await self._cleanup_mcp()

    async def _execute_step(self, step: StepSpec, max_turns: int) -> None:
        """Execute a single scenario step."""
        if step.action == "inject_user":
            content = step.params.get("content", "")
            self._add_user_message(content)

        elif step.action == "await_agent":
            await self._get_agent_response(max_tool_calls=10)

        elif step.action == "await_user":
            # Interactive mode - skip in batch execution
            logger.debug("Skipping await_user step (batch mode)")

    def _add_user_message(self, content: str) -> None:
        """Add a user message to history."""
        self.history.append(Message(role="user", content=content))
        self.events.append(ScenarioEvent(type="user", payload={"content": content}))

    async def _get_agent_response(self, max_tool_calls: int = 10) -> None:
        """Get agent response, handling tool calls."""
        from sandboxy.core.state import Message as CoreMessage
        from sandboxy.core.state import ToolCall

        tool_calls_made = 0

        while tool_calls_made < max_tool_calls:
            # Build tool schemas
            tool_schemas = self._get_tool_schemas()

            # Convert history to CoreMessage objects for agent
            history_for_agent: list[CoreMessage] = []
            for m in self.history:
                # Convert tool_calls from dicts to ToolCall objects if present
                tool_calls_obj = None
                if m.tool_calls:
                    tool_calls_obj = [
                        ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc["arguments"],
                        )
                        for tc in m.tool_calls
                    ]

                history_for_agent.append(
                    CoreMessage(
                        role=m.role,  # type: ignore[arg-type]
                        content=m.content,
                        tool_name=m.tool_name,
                        tool_call_id=m.tool_call_id,
                        tool_calls=tool_calls_obj,
                    )
                )

            # Get agent action
            action: AgentAction = self.agent.step(history_for_agent, tool_schemas)

            if action.type == "message":
                # Agent responded with a message
                self.history.append(Message(role="assistant", content=action.content or ""))
                self.events.append(ScenarioEvent(type="agent", payload={"content": action.content}))
                return

            if action.type == "tool_call":
                # Agent made a tool call
                await self._handle_tool_call(action)
                tool_calls_made += 1

            elif action.type == "stop":
                return

    async def _handle_tool_call(self, action: AgentAction) -> None:
        """Handle a tool call from the agent."""
        tool_name = action.tool_name or ""
        tool_action = action.tool_action or "call"
        tool_args = action.tool_args or {}

        # Generate tool call ID
        tool_call_id = f"call_{tool_name}_{len(self.events)}"
        function_name = f"{tool_name}__{tool_action}"

        # Log the call
        call_log: dict[str, Any] = {
            "tool": tool_name,
            "action": tool_action,
            "args": tool_args,
            "state_before": self.env_state.copy(),
        }

        self.events.append(
            ScenarioEvent(
                type="tool_call",
                payload={"tool": tool_name, "action": tool_action, "args": tool_args},
            )
        )

        # Add assistant message with tool call
        self.history.append(
            Message(
                role="assistant",
                content="",
                tool_calls=[
                    {
                        "id": tool_call_id,
                        "name": function_name,
                        "arguments": json.dumps(tool_args),
                    }
                ],
            )
        )

        # Execute the tool
        if tool_name in self.tools:
            tool = self.tools[tool_name]

            # Check if tool is async (MCP) or sync (YAML mock)
            if hasattr(tool, "invoke_async"):
                # MCP tool - async
                result: ToolResult = await tool.invoke_async(tool_action, tool_args, self.env_state)
            else:
                # YAML mock tool - sync
                result = tool.invoke(tool_action, tool_args, self.env_state)

            call_log["result"] = result.model_dump()
            call_log["state_after"] = self.env_state.copy()

            self.events.append(
                ScenarioEvent(
                    type="tool_result",
                    payload={
                        "tool": tool_name,
                        "action": tool_action,
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                    },
                )
            )

            # Add tool result to history
            result_content = result.data if result.success else (result.error or "")
            if not isinstance(result_content, str):
                result_content = json.dumps(result_content)

            self.history.append(
                Message(
                    role="tool",
                    content=result_content,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
            )
        else:
            # Tool not found
            error_msg = f"Tool not found: {tool_name}"
            call_log["error"] = error_msg

            self.events.append(
                ScenarioEvent(
                    type="tool_result",
                    payload={"tool": tool_name, "success": False, "error": error_msg},
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

        self.tool_call_log.append(call_log)

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for agent."""
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

    def _evaluate_goals(self) -> list[str]:
        """Evaluate which goals were achieved."""
        achieved: list[str] = []

        for goal in self.scenario.goals:
            detection = goal.detection
            if not detection:
                continue

            detection_type = detection.get("type", "")

            if detection_type == "env_state":
                # Check if state key equals value
                key = detection.get("key", "")
                expected = detection.get("value")
                if self.env_state.get(key) == expected:
                    achieved.append(goal.id)

            elif detection_type == "tool_called":
                # Check if a tool was called
                tool = detection.get("tool", "")
                for call in self.tool_call_log:
                    if call.get("tool") == tool:
                        achieved.append(goal.id)
                        break

            elif detection_type == "any_tool_called":
                # Check if any of the listed tools was called
                tools = detection.get("tools", [])
                for call in self.tool_call_log:
                    if call.get("tool") in tools:
                        achieved.append(goal.id)
                        break

            elif detection_type == "agent_contains":
                # Check if agent messages contain patterns
                patterns = detection.get("patterns", [])
                agent_text = " ".join(
                    e.payload.get("content", "") for e in self.events if e.type == "agent"
                ).lower()

                for pattern in patterns:
                    if pattern.lower() in agent_text:
                        achieved.append(goal.id)
                        break

        return list(set(achieved))  # Deduplicate

    def _compute_score(self, goals_achieved: list[str]) -> float:
        """Compute score based on achieved goals."""
        from sandboxy.core.safe_eval import EvaluationError, safe_eval_formula

        total = 0.0
        goal_map = {g.id: g for g in self.scenario.goals}

        for goal_id in goals_achieved:
            if goal_id in goal_map:
                total += goal_map[goal_id].points

        # Apply scoring formula if present
        formula = self.scenario.scoring.get("formula")
        if formula:
            context = {
                g.id.replace("-", "_"): 1.0 if g.id in goals_achieved else 0.0
                for g in self.scenario.goals
            }
            context["goals_achieved"] = float(len(goals_achieved))
            context["total_goals"] = float(len(self.scenario.goals))
            try:
                total = safe_eval_formula(formula, context)
            except EvaluationError as e:
                logger.warning("Failed to evaluate scoring formula '%s': %s", formula, e)

        return total
