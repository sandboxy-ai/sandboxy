"""Unified scenario runner - handles all scenario variations based on YAML structure.

This module provides a single runner that can handle:
- Single-turn prompts
- Multi-turn conversations with tools
- Goal-based and judge-based evaluation
- Multi-model comparison with statistical runs
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from sandboxy.providers import get_registry
from sandboxy.tools.loader import get_tool_dirs

logger = logging.getLogger(__name__)


def _get_style_prompt(style: str) -> str:
    """Get a simple style prompt modifier."""
    styles = {
        "brief": "Keep your response brief and to the point.",
        "detailed": "Provide a detailed, comprehensive response.",
        "technical": "Be technical and precise in your response.",
        "casual": "Respond in a casual, friendly manner.",
    }
    return styles.get(style, f"Respond in a {style} manner.")


def generate_tool_call_id() -> str:
    """Generate a tool call ID compatible with all providers.

    Some providers (e.g., Mistral) require IDs to be exactly 9 alphanumeric characters.
    """
    # Use UUID and take first 9 alphanumeric characters
    raw = uuid.uuid4().hex[:9]  # hex is already alphanumeric (0-9, a-f)
    return raw


# =============================================================================
# Data Models
# =============================================================================


class JudgeSpec(BaseModel):
    """Specification for a judge (LLM or rule-based)."""

    type: str = "llm"  # llm, contains, regex, exact, length, consensus, computed
    model: str | None = None  # For LLM judge
    rubric: str = ""  # Scoring rubric for LLM judge
    pattern: str | None = None  # For contains, regex, exact
    case_sensitive: bool = False
    min_length: int | None = None  # For length judge
    max_length: int | None = None
    voters: list[str] = Field(default_factory=list)  # For consensus judge
    helper: str | None = None  # For computed judge
    pass_threshold: float = 0.5


class GoalSpec(BaseModel):
    """Specification for a goal (rule-based evaluation)."""

    id: str
    name: str = ""
    description: str = ""
    points: int = 0
    detection: dict[str, Any] = Field(default_factory=dict)
    outcome: bool = False  # Mutually exclusive outcome goal (for dataset benchmarking)


class StepSpec(BaseModel):
    """Specification for a conversation step."""

    id: str
    action: str  # inject_user, await_user, await_agent, branch
    params: dict[str, Any] = Field(default_factory=dict)


class EvaluationSpec(BaseModel):
    """Evaluation configuration combining goals and judge."""

    goals: list[GoalSpec] = Field(default_factory=list)
    judge: JudgeSpec | None = None
    max_score: float | None = None
    formula: str | None = None


class McpServerSpec(BaseModel):
    """MCP server connection specification."""

    name: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    transport: str = "auto"


class VariableSpec(BaseModel):
    """Variable specification for scenario parameters."""

    name: str
    label: str = ""
    type: str = "string"  # string, number, boolean, select, slider
    default: Any = None
    options: list[str] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None
    step: float | None = None


class UnifiedScenarioSpec(BaseModel):
    """Unified scenario specification.

    The structure determines behavior:
    - prompt only → single-turn
    - steps → multi-turn
    - tools/tools_from → enable tool use
    - evaluation.goals → goal-based scoring
    - evaluation.judge → LLM/rule-based judging
    - style → response style constraint
    """

    # Metadata
    id: str
    name: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    variables: list[VariableSpec] = Field(default_factory=list)

    # Agent configuration
    system_prompt: str = ""

    # Interaction (one of these)
    prompt: str | None = None  # Simple single-turn
    steps: list[StepSpec] = Field(default_factory=list)  # Multi-turn

    # Tools
    tools: dict[str, Any] = Field(default_factory=dict)  # Inline definitions
    tools_from: list[str] = Field(default_factory=list)  # Library imports
    mcp_servers: list[McpServerSpec] = Field(default_factory=list)

    # State
    initial_state: dict[str, Any] = Field(default_factory=dict)

    # Evaluation
    evaluation: EvaluationSpec = Field(default_factory=EvaluationSpec)

    # Style (for blitz-like runs)
    style: str | None = None

    # Events (for chaos injection)
    events: dict[str, Any] = Field(default_factory=dict)

    def has_steps(self) -> bool:
        """Check if this is a multi-turn scenario."""
        return len(self.steps) > 0

    def has_tools(self) -> bool:
        """Check if this scenario uses tools."""
        return bool(self.tools) or bool(self.tools_from) or bool(self.mcp_servers)

    def has_evaluation(self) -> bool:
        """Check if this scenario has evaluation configured."""
        return bool(self.evaluation.goals) or self.evaluation.judge is not None

    def has_goals(self) -> bool:
        """Check if this scenario has goal-based evaluation."""
        return bool(self.evaluation.goals)

    def has_judge(self) -> bool:
        """Check if this scenario has a judge configured."""
        return self.evaluation.judge is not None


# =============================================================================
# Result Models
# =============================================================================


@dataclass
class Message:
    """A message in conversation history."""

    role: str  # system, user, assistant, tool
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ToolCallRecord:
    """Record of a tool call."""

    tool: str
    action: str
    args: dict[str, Any]
    result: Any = None
    success: bool = True
    error: str | None = None


@dataclass
class GoalResult:
    """Result of evaluating a single goal."""

    id: str
    name: str
    achieved: bool
    points: int
    reason: str = ""


@dataclass
class JudgeResult:
    """Result from judge evaluation."""

    score: float
    passed: bool
    reasoning: str
    judge_type: str


@dataclass
class EvaluationResult:
    """Combined evaluation result."""

    goals: list[GoalResult] = field(default_factory=list)
    judge: JudgeResult | None = None
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "achieved": g.achieved,
                    "points": g.points,
                    "reason": g.reason,
                }
                for g in self.goals
            ],
            "judge": {
                "score": self.judge.score,
                "passed": self.judge.passed,
                "reasoning": self.judge.reasoning,
                "judge_type": self.judge.judge_type,
            }
            if self.judge
            else None,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
        }


@dataclass
class RunResult:
    """Result of running a single scenario with a single model."""

    id: str
    scenario_id: str
    model: str
    prompt: str | None = None
    response: str = ""
    history: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    evaluation: EvaluationResult | None = None
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "model": self.model,
            "prompt": self.prompt,
            "response": self.response,
            "history": [
                {"role": m.role, "content": m.content, "tool_name": m.tool_name}
                for m in self.history
            ],
            "tool_calls": [
                {
                    "tool": tc.tool,
                    "action": tc.action,
                    "args": tc.args,
                    "result": tc.result,
                    "success": tc.success,
                    "error": tc.error,
                }
                for tc in self.tool_calls
            ],
            "final_state": self.final_state,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def pretty(self) -> str:
        """Format for human-readable display."""
        lines = [
            f"Scenario: {self.scenario_id}",
            f"Model: {self.model}",
            f"Latency: {self.latency_ms}ms",
        ]

        if self.prompt:
            lines.append(f"Prompt: {self.prompt[:100]}{'...' if len(self.prompt) > 100 else ''}")

        if self.response:
            resp = self.response[:200] + "..." if len(self.response) > 200 else self.response
            lines.append(f"Response: {resp}")

        if self.tool_calls:
            lines.append(f"Tool Calls: {len(self.tool_calls)}")

        if self.evaluation:
            lines.append("")
            if self.evaluation.goals:
                achieved = sum(1 for g in self.evaluation.goals if g.achieved)
                lines.append(f"Goals: {achieved}/{len(self.evaluation.goals)}")
            if self.evaluation.judge:
                lines.append(f"Judge Score: {self.evaluation.judge.score:.2f}")
            lines.append(
                f"Total Score: {self.evaluation.total_score:.1f}/{self.evaluation.max_score:.1f}"
            )
            lines.append(f"Percentage: {self.evaluation.percentage:.1f}%")

        if self.error:
            lines.append(f"Error: {self.error}")

        return "\n".join(lines)


# =============================================================================
# Unified Runner
# =============================================================================


class UnifiedRunner:
    """Single runner that handles all scenario variations.

    Example:
        runner = UnifiedRunner()

        # Single model run
        result = await runner.run(scenario, model="gpt-4o")

        # Multi-model comparison
        comparison = await runner.run_comparison(
            scenario,
            models=["gpt-4o", "claude-3.5-sonnet"],
            runs_per_model=3,
        )

    """

    def __init__(self, tool_dirs: list[Path] | None = None) -> None:
        """Initialize the runner.

        Args:
            tool_dirs: Directories to search for tool libraries

        """
        self.tool_dirs = tool_dirs or get_tool_dirs()
        self._registry = None

    @property
    def registry(self) -> Any:
        """Get or create the provider registry."""
        if self._registry is None:
            self._registry = get_registry()
        return self._registry

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate cost in USD based on model pricing.

        Uses pricing data from OpenRouter models registry.
        """
        try:
            from sandboxy.providers.openrouter import OPENROUTER_MODELS

            model_info = OPENROUTER_MODELS.get(model)
            if not model_info or not model_info.input_cost_per_million:
                return None

            input_cost = (input_tokens / 1_000_000) * model_info.input_cost_per_million
            output_cost = (output_tokens / 1_000_000) * model_info.output_cost_per_million
            return round(input_cost + output_cost, 6)
        except ImportError:
            return None

    async def run(
        self,
        scenario: UnifiedScenarioSpec,
        model: str,
        variables: dict[str, Any] | None = None,
        max_turns: int = 20,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        tool_overrides: dict[str, Any] | None = None,
        expected_outcome: str | None = None,
    ) -> RunResult:
        """Run a scenario with a single model.

        Args:
            scenario: The scenario specification
            model: Model ID to use
            variables: Variable substitutions
            max_turns: Maximum conversation turns
            max_tokens: Maximum tokens per response
            temperature: Sampling temperature
            tool_overrides: Optional dict mapping "tool.action" to override response data.
                           Used by dataset benchmarking to inject test case data.
            expected_outcome: Optional expected outcome goal ID for dataset benchmarking.
                             When set, only this outcome goal is evaluated (others skipped).

        Returns:
            RunResult with response and evaluation

        """
        start_time = time.perf_counter()
        run_id = str(uuid.uuid4())

        # Apply variable substitutions
        scenario = self._apply_variables(scenario, variables or {})

        try:
            if scenario.has_steps():
                result = await self._run_multi_turn(
                    scenario, model, max_turns, max_tokens, temperature, tool_overrides
                )
            else:
                result = await self._run_single_turn(scenario, model, max_tokens, temperature)

            # Run evaluation if configured
            if scenario.has_evaluation():
                result.evaluation = await self._evaluate(result, scenario, expected_outcome)

            result.id = run_id
            result.latency_ms = int((time.perf_counter() - start_time) * 1000)
            return result

        except Exception as e:
            logger.exception(f"Run failed for {model}: {e}")
            return RunResult(
                id=run_id,
                scenario_id=scenario.id,
                model=model,
                error=str(e),
                latency_ms=int((time.perf_counter() - start_time) * 1000),
            )

    async def _run_single_turn(
        self,
        scenario: UnifiedScenarioSpec,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> RunResult:
        """Execute a single-turn prompt."""
        prompt = scenario.prompt or ""

        # Build system prompt with optional style
        system_prompt = scenario.system_prompt or ""
        if scenario.style:
            style_instruction = _get_style_prompt(scenario.style)
            system_prompt = f"{system_prompt}\n\n{style_instruction}".strip()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Call model
        provider = self.registry.get_provider_for_model(model)
        response = await provider.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return RunResult(
            id="",  # Set by caller
            scenario_id=scenario.id,
            model=model,
            prompt=prompt,
            response=response.content,
            history=[
                Message(role="user", content=prompt),
                Message(role="assistant", content=response.content),
            ],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )

    async def _run_multi_turn(
        self,
        scenario: UnifiedScenarioSpec,
        model: str,
        max_turns: int,
        max_tokens: int,
        temperature: float,
        tool_overrides: dict[str, Any] | None = None,
    ) -> RunResult:
        """Execute a multi-turn scenario with tools."""
        from sandboxy.agents.base import AgentAction
        from sandboxy.agents.loader import create_agent_from_model
        from sandboxy.core.state import Message as CoreMessage
        from sandboxy.core.state import ToolCall
        from sandboxy.tools.yaml_tools import load_scenario_tools

        # Load tools with optional overrides for dataset benchmarking
        scenario_data = {
            "tools_from": scenario.tools_from,
            "tools": scenario.tools,
        }
        tools = load_scenario_tools(scenario_data, self.tool_dirs, tool_overrides)

        # Load MCP tools if configured
        mcp_manager = None
        if scenario.mcp_servers:
            try:
                from sandboxy.mcp.client import McpManager, McpServerConfig

                mcp_manager = McpManager()
                configs = [
                    McpServerConfig(
                        name=s.name,
                        command=s.command,
                        args=s.args,
                        env=s.env,
                        url=s.url,
                        headers=s.headers,
                        transport=s.transport,  # type: ignore
                    )
                    for s in scenario.mcp_servers
                ]
                mcp_tools = await mcp_manager.connect_all(configs)
                for name, tool in mcp_tools.items():
                    if name not in tools:
                        tools[name] = tool
            except ImportError:
                logger.warning("MCP client not available")

        try:
            # Enhance system prompt when tools are available
            system_prompt = scenario.system_prompt or ""

            # Apply style if specified
            if scenario.style:
                style_instruction = _get_style_prompt(scenario.style)
                system_prompt = f"{system_prompt}\n\n{style_instruction}".strip()

            if tools:
                tool_instruction = (
                    "\n\n---\n"
                    "IMPORTANT: You have tools available to take actions. "
                    "Do NOT just describe what commands to run or what steps to take. "
                    "Instead, USE YOUR TOOLS to actually execute actions, gather information, "
                    "and accomplish tasks directly. Act autonomously rather than giving instructions."
                )
                if tool_instruction not in system_prompt:
                    system_prompt = system_prompt + tool_instruction

            # Create agent (use model ID directly)
            agent = create_agent_from_model(model, system_prompt=system_prompt)

            # Reset usage tracking if agent supports it
            if hasattr(agent, "reset_usage"):
                agent.reset_usage()

            # Initialize state
            env_state = dict(scenario.initial_state)
            history: list[Message] = []
            tool_call_log: list[ToolCallRecord] = []

            # Add system prompt (use enhanced version with tool instructions)
            if system_prompt:
                history.append(Message(role="system", content=system_prompt))

            # Execute steps
            for step in scenario.steps:
                if step.action == "inject_user":
                    content = step.params.get("content", "")
                    history.append(Message(role="user", content=content))

                elif step.action == "await_agent":
                    # Get agent response with tool loop
                    tool_calls_made = 0
                    max_tool_calls = 10

                    while tool_calls_made < max_tool_calls:
                        # Build tool schemas
                        tool_schemas = [
                            {
                                "name": name,
                                "description": tool.description,
                                "actions": tool.get_actions(),
                            }
                            for name, tool in tools.items()
                        ]

                        # Convert to CoreMessage for agent
                        history_for_agent = [
                            CoreMessage(
                                role=m.role,  # type: ignore
                                content=m.content,
                                tool_name=m.tool_name,
                                tool_call_id=m.tool_call_id,
                                tool_calls=[
                                    ToolCall(
                                        id=tc["id"],
                                        name=tc["name"],
                                        arguments=tc["arguments"],
                                    )
                                    for tc in m.tool_calls
                                ]
                                if m.tool_calls
                                else None,
                            )
                            for m in history
                        ]

                        # Get agent action
                        action: AgentAction = agent.step(
                            history_for_agent, tool_schemas if tools else None
                        )

                        if action.type == "message":
                            history.append(Message(role="assistant", content=action.content or ""))
                            break

                        if action.type == "tool_call":
                            tool_name = action.tool_name or ""
                            tool_action = action.tool_action or "call"
                            tool_args = action.tool_args or {}

                            tool_call_id = generate_tool_call_id()
                            function_name = f"{tool_name}__{tool_action}"

                            # Add assistant message with tool call
                            history.append(
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

                            # Execute tool
                            if tool_name in tools:
                                tool = tools[tool_name]
                                if hasattr(tool, "invoke_async"):
                                    result = await tool.invoke_async(
                                        tool_action, tool_args, env_state
                                    )
                                else:
                                    result = tool.invoke(tool_action, tool_args, env_state)

                                tool_call_log.append(
                                    ToolCallRecord(
                                        tool=tool_name,
                                        action=tool_action,
                                        args=tool_args,
                                        result=result.data,
                                        success=result.success,
                                        error=result.error,
                                    )
                                )

                                result_content = (
                                    result.data if result.success else (result.error or "")
                                )
                                if not isinstance(result_content, str):
                                    result_content = json.dumps(result_content)

                                history.append(
                                    Message(
                                        role="tool",
                                        content=result_content,
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                    )
                                )
                            else:
                                error_msg = f"Tool not found: {tool_name}"
                                tool_call_log.append(
                                    ToolCallRecord(
                                        tool=tool_name,
                                        action=tool_action,
                                        args=tool_args,
                                        success=False,
                                        error=error_msg,
                                    )
                                )
                                history.append(
                                    Message(
                                        role="tool",
                                        content=error_msg,
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                    )
                                )

                            tool_calls_made += 1

                        elif action.type == "stop":
                            break

                elif step.action == "await_user":
                    # Skip in batch mode
                    logger.debug("Skipping await_user step (batch mode)")

            # Get final response text
            response_text = ""
            for msg in reversed(history):
                if msg.role == "assistant" and msg.content:
                    response_text = msg.content
                    break

            # Get token usage from agent
            input_tokens = 0
            output_tokens = 0
            cost_usd = None
            if hasattr(agent, "get_usage"):
                usage = agent.get_usage()
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                # Calculate cost from token counts
                cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            return RunResult(
                id="",
                scenario_id=scenario.id,
                model=model,
                response=response_text,
                history=history,
                tool_calls=tool_call_log,
                final_state=env_state,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )

        finally:
            if mcp_manager:
                await mcp_manager.disconnect_all()

    async def _evaluate(
        self,
        result: RunResult,
        scenario: UnifiedScenarioSpec,
        expected_outcome: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a run result.

        Args:
            result: The run result to evaluate
            scenario: The scenario specification
            expected_outcome: Optional expected outcome goal ID for dataset benchmarking.
                             When set, only evaluates this outcome goal (others skipped).

        """
        eval_result = EvaluationResult()

        # Goal-based evaluation
        if scenario.has_goals():
            # Separate process goals from outcome goals
            process_goals = [g for g in scenario.evaluation.goals if not g.outcome]
            outcome_goals = [g for g in scenario.evaluation.goals if g.outcome]

            # Always evaluate process goals
            for goal in process_goals:
                goal_result = self._evaluate_goal(goal, result)
                eval_result.goals.append(goal_result)

            # Handle outcome goals based on expected_outcome
            if expected_outcome:
                # Only evaluate the expected outcome goal
                for goal in outcome_goals:
                    if goal.id == expected_outcome:
                        goal_result = self._evaluate_goal(goal, result)
                        eval_result.goals.append(goal_result)
                        break
            else:
                # No expected outcome - evaluate all outcome goals (backward compatible)
                for goal in outcome_goals:
                    goal_result = self._evaluate_goal(goal, result)
                    eval_result.goals.append(goal_result)

            # Calculate goal score
            eval_result.total_score = sum(g.points for g in eval_result.goals if g.achieved)

            # Max score = process goals + only the expected outcome goal (if specified)
            if expected_outcome:
                eval_result.max_score = sum(g.points for g in process_goals)
                for g in outcome_goals:
                    if g.id == expected_outcome:
                        eval_result.max_score += g.points
                        break
            else:
                eval_result.max_score = sum(g.points for g in scenario.evaluation.goals)

        # Judge-based evaluation
        if scenario.has_judge():
            judge = scenario.evaluation.judge
            assert judge is not None

            if judge.type == "llm":
                judge_result = await self._judge_with_llm(judge, result, scenario)
            elif judge.type == "contains":
                judge_result = self._judge_with_contains(judge, result)
            elif judge.type == "regex":
                judge_result = self._judge_with_regex(judge, result)
            elif judge.type == "exact":
                judge_result = self._judge_with_exact(judge, result)
            elif judge.type == "length":
                judge_result = self._judge_with_length(judge, result)
            else:
                judge_result = JudgeResult(
                    score=0.5,
                    passed=True,
                    reasoning=f"Unknown judge type: {judge.type}",
                    judge_type=judge.type,
                )

            eval_result.judge = judge_result

            # If no goals, use judge score
            if not scenario.has_goals():
                # Scale judge score (0-1) to max_score or 100
                max_score = scenario.evaluation.max_score or 100
                eval_result.total_score = judge_result.score * max_score
                eval_result.max_score = max_score

        # Calculate percentage
        if eval_result.max_score > 0:
            eval_result.percentage = (eval_result.total_score / eval_result.max_score) * 100

        return eval_result

    def _evaluate_goal(self, goal: GoalSpec, result: RunResult) -> GoalResult:
        """Evaluate a single goal."""
        detection = goal.detection
        detection_type = detection.get("type", "")
        achieved = False
        reason = ""

        if detection_type == "env_state":
            key = detection.get("key", "")
            expected = detection.get("value")
            actual = result.final_state.get(key)
            achieved = actual == expected
            reason = f"State[{key}] = {actual} (expected {expected})"

        elif detection_type == "tool_called":
            tool = detection.get("tool", "")
            action = detection.get("action")
            for tc in result.tool_calls:
                if tc.tool == tool and (action is None or tc.action == action):
                    achieved = True
                    reason = f"Tool {tool} was called"
                    break
            if not achieved:
                reason = f"Tool {tool} was not called"

        elif detection_type == "any_tool_called":
            # Supports both "tool_name" and "tool_name.action" formats
            tools = detection.get("tools", [])
            for tc in result.tool_calls:
                call_combined = f"{tc.tool}.{tc.action}"
                # Match against tool name, action, or combined format
                if tc.tool in tools or tc.action in tools or call_combined in tools:
                    achieved = True
                    reason = f"Tool {call_combined} was called"
                    break
            if not achieved:
                reason = f"None of {tools} were called"

        elif detection_type == "agent_contains":
            patterns = detection.get("patterns", [])
            agent_text = " ".join(
                m.content for m in result.history if m.role == "assistant" and m.content
            ).lower()

            for pattern in patterns:
                # Convert to string in case YAML parsed as int (e.g., 10000 without quotes)
                pattern_str = str(pattern).lower()
                if pattern_str in agent_text:
                    achieved = True
                    reason = f"Agent response contains '{pattern}'"
                    break
            if not achieved:
                reason = f"Agent response does not contain any of {patterns}"

        elif detection_type == "tool_sequence":
            # Check if certain tools were called before others
            required_before = detection.get("required_before", {})
            tool_order = [tc.tool for tc in result.tool_calls]

            all_satisfied = True
            for tool, prereqs in required_before.items():
                tool_idx = None
                for i, t in enumerate(tool_order):
                    if t == tool:
                        tool_idx = i
                        break

                if tool_idx is not None:
                    for prereq in prereqs:
                        prereq_idx = None
                        for i, t in enumerate(tool_order):
                            if t == prereq:
                                prereq_idx = i
                                break
                        if prereq_idx is None or prereq_idx > tool_idx:
                            all_satisfied = False
                            reason = f"{prereq} should be called before {tool}"
                            break

            achieved = all_satisfied
            if achieved:
                reason = "Tool sequence requirements met"

        return GoalResult(
            id=goal.id,
            name=goal.name or goal.id,
            achieved=achieved,
            points=goal.points if achieved else 0,
            reason=reason,
        )

    async def _judge_with_llm(
        self,
        judge: JudgeSpec,
        result: RunResult,
        scenario: UnifiedScenarioSpec,
    ) -> JudgeResult:
        """Judge using LLM-as-a-judge."""
        model = judge.model or "gpt-4o-mini"
        rubric = judge.rubric or "Score the response from 0.0 to 1.0 based on quality."

        # Build judge prompt
        prompt_text = scenario.prompt or ""
        if not prompt_text and result.history:
            # Get first user message
            for msg in result.history:
                if msg.role == "user":
                    prompt_text = msg.content
                    break

        # Build tool calls summary for judge
        tool_calls_summary = ""
        if result.tool_calls:
            tool_lines = []
            for tc in result.tool_calls:
                status = "SUCCESS" if tc.success else "FAILED"
                tool_lines.append(f"  - {tc.tool}.{tc.action}({tc.args}) -> {status}")
            tool_calls_summary = "\n".join(tool_lines)

        judge_prompt = f"""You are evaluating an AI model's response.

ORIGINAL PROMPT:
{prompt_text}

TOOLS CALLED BY MODEL:
{tool_calls_summary if tool_calls_summary else "(No tools were called)"}

MODEL FINAL RESPONSE:
{result.response}

EVALUATION RUBRIC:
{rubric}

Evaluate the response and provide your assessment in this exact JSON format:
{{"score": <0.0-1.0>, "passed": <true/false>, "reasoning": "<brief explanation>"}}

Respond with ONLY the JSON, no other text."""

        try:
            provider = self.registry.get_provider_for_model(model)
            # Shield from external cancellation (e.g., MCP's anyio cancel scopes)
            response = await asyncio.shield(
                provider.complete(
                    model=model,
                    messages=[{"role": "user", "content": judge_prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )
            )

            # Parse JSON
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)
            return JudgeResult(
                score=float(data.get("score", 0.5)),
                passed=bool(data.get("passed", True)),
                reasoning=str(data.get("reasoning", "No reasoning")),
                judge_type="llm",
            )

        except asyncio.CancelledError as e:
            # MCP's anyio cancel scopes can cancel our HTTP calls
            logger.warning(f"LLM judge cancelled (likely MCP cleanup issue): {e}")
            return JudgeResult(
                score=0.5,
                passed=True,
                reasoning="Judge skipped: async operation was cancelled",
                judge_type="llm",
            )
        except Exception as e:
            logger.error(f"LLM judge error: {e}")
            return JudgeResult(
                score=0.5,
                passed=True,
                reasoning=f"Judge error: {e}",
                judge_type="llm",
            )

    def _judge_with_contains(self, judge: JudgeSpec, result: RunResult) -> JudgeResult:
        """Judge by checking if response contains pattern."""
        pattern = judge.pattern or ""
        response = result.response

        if not judge.case_sensitive:
            response = response.lower()
            pattern = pattern.lower()

        found = pattern in response
        return JudgeResult(
            score=1.0 if found else 0.0,
            passed=found,
            reasoning=f"Contains '{judge.pattern}': {found}",
            judge_type="contains",
        )

    def _judge_with_regex(self, judge: JudgeSpec, result: RunResult) -> JudgeResult:
        """Judge by regex pattern match."""
        import re

        pattern = judge.pattern or ".*"
        flags = 0 if judge.case_sensitive else re.IGNORECASE

        try:
            match = re.search(pattern, result.response, flags)
            found = match is not None
            return JudgeResult(
                score=1.0 if found else 0.0,
                passed=found,
                reasoning=f"Regex match: {found}",
                judge_type="regex",
            )
        except re.error as e:
            return JudgeResult(
                score=0.0,
                passed=False,
                reasoning=f"Invalid regex: {e}",
                judge_type="regex",
            )

    def _judge_with_exact(self, judge: JudgeSpec, result: RunResult) -> JudgeResult:
        """Judge by exact match."""
        expected = judge.pattern or ""
        response = result.response.strip()

        if not judge.case_sensitive:
            expected = expected.lower()
            response = response.lower()

        match = response == expected
        return JudgeResult(
            score=1.0 if match else 0.0,
            passed=match,
            reasoning=f"Exact match: {match}",
            judge_type="exact",
        )

    def _judge_with_length(self, judge: JudgeSpec, result: RunResult) -> JudgeResult:
        """Judge by response length."""
        length = len(result.response)
        reasons = []

        passes_min = judge.min_length is None or length >= judge.min_length
        passes_max = judge.max_length is None or length <= judge.max_length

        if not passes_min:
            reasons.append(f"too short ({length} < {judge.min_length})")
        if not passes_max:
            reasons.append(f"too long ({length} > {judge.max_length})")

        passed = passes_min and passes_max
        reasoning = f"Length: {length} chars"
        if reasons:
            reasoning += f" - {', '.join(reasons)}"

        return JudgeResult(
            score=1.0 if passed else 0.0,
            passed=passed,
            reasoning=reasoning,
            judge_type="length",
        )

    def _apply_variables(
        self,
        scenario: UnifiedScenarioSpec,
        variables: dict[str, Any],
    ) -> UnifiedScenarioSpec:
        """Apply variable substitutions to scenario."""
        import re

        def interpolate(text: str) -> str:
            if not isinstance(text, str):
                return text

            def replace(match: re.Match[str]) -> str:
                key = match.group(1)
                if key in variables:
                    return str(variables[key])
                return match.group(0)

            return re.sub(r"\{(\w+)\}", replace, text)

        def interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                return interpolate(value)
            if isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [interpolate_value(item) for item in value]
            return value

        # Create new spec with interpolated values
        new_steps = [
            StepSpec(
                id=s.id,
                action=s.action,
                params=interpolate_value(dict(s.params)),
            )
            for s in scenario.steps
        ]

        return UnifiedScenarioSpec(
            id=scenario.id,
            name=scenario.name,
            description=interpolate(scenario.description),
            category=scenario.category,
            tags=scenario.tags,
            variables=scenario.variables,
            system_prompt=interpolate(scenario.system_prompt),
            prompt=interpolate(scenario.prompt) if scenario.prompt else None,
            steps=new_steps,
            tools=scenario.tools,
            tools_from=scenario.tools_from,
            mcp_servers=scenario.mcp_servers,
            initial_state=interpolate_value(dict(scenario.initial_state)),
            evaluation=scenario.evaluation,
            style=scenario.style,
            events=scenario.events,
        )


# =============================================================================
# Loader Functions
# =============================================================================


def load_unified_scenario(path: Path) -> UnifiedScenarioSpec:
    """Load a unified scenario from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        UnifiedScenarioSpec

    Raises:
        ValueError: If file cannot be loaded or parsed

    """
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e
    except FileNotFoundError as e:
        raise ValueError(f"File not found: {path}") from e

    if not isinstance(raw, dict):
        raise ValueError("Scenario must be a YAML mapping")

    return parse_unified_scenario(raw)


def parse_unified_scenario(raw: dict[str, Any]) -> UnifiedScenarioSpec:
    """Parse raw YAML into UnifiedScenarioSpec.

    Supports multiple scenario formats:
    - Standard: system_prompt, tools, evaluation.goals
    - Alternate: agent.system_prompt, environment.tools, evaluation list with kind:
    """
    # Parse tools_from
    tools_from = raw.get("tools_from", [])
    if isinstance(tools_from, str):
        tools_from = [tools_from]

    # Support alternate system_prompt location (agent.system_prompt)
    system_prompt = raw.get("system_prompt", "")
    if not system_prompt:
        agent_config = raw.get("agent", {})
        if isinstance(agent_config, dict):
            system_prompt = agent_config.get("system_prompt", "")

    # Support alternate tools location (environment.tools)
    tools = raw.get("tools", {})
    if not tools:
        env_config = raw.get("environment", {})
        if isinstance(env_config, dict):
            env_tools = env_config.get("tools", [])
            # Convert environment.tools format to standard format
            if isinstance(env_tools, list):
                for tool_def in env_tools:
                    if isinstance(tool_def, dict):
                        tool_name = tool_def.get("name", "")
                        tool_config = tool_def.get("config", {})
                        tool_actions = tool_config.get("tools", {})
                        if tool_name and tool_actions:
                            # Convert to standard inline tools format
                            tools[tool_name] = {
                                "description": f"{tool_name} tools",
                                "actions": tool_actions,
                            }

    # Support alternate initial_state location (environment.initial_state)
    initial_state = raw.get("initial_state", {})
    if not initial_state:
        env_config = raw.get("environment", {})
        if isinstance(env_config, dict):
            initial_state = env_config.get("initial_state", {})

    # Parse MCP servers
    mcp_servers = []
    for server in raw.get("mcp_servers", []):
        if isinstance(server, dict):
            mcp_servers.append(
                McpServerSpec(
                    name=server.get("name", "unnamed"),
                    command=server.get("command"),
                    args=server.get("args", []),
                    env=server.get("env", {}),
                    url=server.get("url"),
                    headers=server.get("headers", {}),
                    transport=server.get("transport", "auto"),
                )
            )

    # Parse steps
    steps = []
    for s in raw.get("steps", []):
        steps.append(
            StepSpec(
                id=s.get("id", f"step_{len(steps)}"),
                action=s.get("action", "await_agent"),
                params=s.get("params", {}),
            )
        )

    # Parse variables
    variables = []
    for v in raw.get("variables", []):
        variables.append(
            VariableSpec(
                name=v.get("name", ""),
                label=v.get("label", ""),
                type=v.get("type", "string"),
                default=v.get("default"),
                options=v.get("options", []),
                min=v.get("min"),
                max=v.get("max"),
                step=v.get("step"),
            )
        )

    # Parse evaluation
    evaluation_raw = raw.get("evaluation", {})
    # Handle case where evaluation is a list (of goals) instead of a dict
    if isinstance(evaluation_raw, list):
        goals_raw = evaluation_raw
        evaluation_raw = {}
    else:
        goals_raw = evaluation_raw.get("goals", []) or raw.get("goals", [])
    goals = []
    for g in goals_raw:
        # Support alternate format with 'kind:' instead of 'detection.type:'
        detection = g.get("detection", {})
        if not detection and "kind" in g:
            # Convert alternate format: kind, tool, action, key, value, target
            kind = g.get("kind", "")
            if kind == "tool_called":
                detection = {
                    "type": "tool_called",
                    "tool": g.get("tool"),
                    "action": g.get("action"),
                }
            elif kind == "env_state":
                detection = {
                    "type": "env_state",
                    "key": g.get("key"),
                    "value": g.get("value"),
                }
            elif kind == "contains":
                detection = {
                    "type": "agent_contains",
                    "patterns": [g.get("value", "")] if g.get("value") else [],
                }
            elif kind == "count":
                detection = {
                    "type": "count",
                    "target": g.get("target"),
                    "max": g.get("max"),
                    "min": g.get("min"),
                }
            else:
                detection = {"type": kind}

        goals.append(
            GoalSpec(
                id=g.get("id", f"goal_{len(goals)}"),
                name=g.get("name", ""),
                description=g.get("description", ""),
                points=g.get("points", 10),  # Default 10 points if not specified
                detection=detection,
                outcome=g.get("outcome", False),  # Mutually exclusive outcome goal
            )
        )

    judge = None
    judge_raw = evaluation_raw.get("judge")
    if judge_raw:
        judge = JudgeSpec(
            type=judge_raw.get("type", "llm"),
            model=judge_raw.get("model"),
            rubric=judge_raw.get("rubric", ""),
            pattern=judge_raw.get("pattern"),
            case_sensitive=judge_raw.get("case_sensitive", False),
            min_length=judge_raw.get("min_length"),
            max_length=judge_raw.get("max_length"),
            voters=judge_raw.get("voters", []),
            helper=judge_raw.get("helper"),
            pass_threshold=judge_raw.get("pass_threshold", 0.5),
        )

    evaluation = EvaluationSpec(
        goals=goals,
        judge=judge,
        max_score=evaluation_raw.get("max_score"),
        formula=evaluation_raw.get("formula"),
    )

    # Get metadata from raw or alternate location
    metadata = raw.get("metadata", {})
    category = raw.get("category", "")
    tags = raw.get("tags", [])
    if not category and isinstance(metadata, dict):
        category = metadata.get("category", "")
    if not tags and isinstance(metadata, dict):
        tags = metadata.get("tags", [])

    return UnifiedScenarioSpec(
        id=raw.get("id", "unnamed"),
        name=raw.get("name", raw.get("id", "Unnamed Scenario")),
        description=raw.get("description", ""),
        category=category,
        tags=tags,
        variables=variables,
        system_prompt=system_prompt,  # Use parsed value (supports agent.system_prompt)
        prompt=raw.get("prompt"),
        steps=steps,
        tools=tools,  # Use parsed value (supports environment.tools)
        tools_from=tools_from,
        mcp_servers=mcp_servers,
        initial_state=initial_state,  # Use parsed value (supports environment.initial_state)
        evaluation=evaluation,
        style=raw.get("style"),
        events=raw.get("events", {}),
    )
