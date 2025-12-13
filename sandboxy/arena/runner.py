"""Arena runner for executing prompts against multiple models."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sandboxy.arena.prompts import ArenaPrompt, JudgeType
from sandboxy.providers import ProviderRegistry, get_registry
from sandboxy.providers.base import ModelResponse, ProviderError

logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


@dataclass
class ModelResult:
    """Result from a single model in an arena run."""

    model_id: str
    response: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "response": self.response,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "error": self.error,
        }


@dataclass
class JudgmentResult:
    """Judgment result for a model's response."""

    model_id: str
    score: float
    passed: bool
    reasoning: str
    judge_type: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "score": self.score,
            "passed": self.passed,
            "reasoning": self.reasoning,
            "judge_type": self.judge_type,
        }


@dataclass
class ArenaRun:
    """Result of an arena run with multiple models."""

    id: str
    prompt_id: str | None
    prompt_text: str
    system_prompt: str | None
    models: list[str]
    results: dict[str, ModelResult]
    judgments: dict[str, JudgmentResult]
    variables: dict[str, Any] | None
    created_at: datetime
    total_latency_ms: int = 0
    total_cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "prompt_text": self.prompt_text,
            "system_prompt": self.system_prompt,
            "models": self.models,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "judgments": {k: v.to_dict() for k, v in self.judgments.items()},
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "total_latency_ms": self.total_latency_ms,
            "total_cost_usd": self.total_cost_usd,
        }

    def get_winner(self) -> str | None:
        """Get the model with the highest score."""
        if not self.judgments:
            return None
        return max(self.judgments.items(), key=lambda x: x[1].score)[0]

    def get_ranking(self) -> list[tuple[str, float]]:
        """Get models ranked by score (highest first)."""
        return sorted(
            [(k, v.score) for k, v in self.judgments.items()],
            key=lambda x: x[1],
            reverse=True,
        )


class ArenaRunner:
    """Run prompts against multiple models in parallel.

    Example:
        runner = ArenaRunner()
        result = await runner.run(
            prompt=ArenaPrompt(text="What is 2+2?"),
            models=["openai/gpt-4o", "anthropic/claude-3-opus"],
        )
        print(f"Winner: {result.get_winner()}")
    """

    def __init__(self, registry: ProviderRegistry | None = None):
        """Initialize arena runner.

        Args:
            registry: Provider registry. Uses global registry if not provided.
        """
        self.registry = registry or get_registry()

    async def run(
        self,
        prompt: ArenaPrompt,
        models: list[str],
        variables: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ArenaRun:
        """Run a prompt against multiple models.

        Args:
            prompt: The prompt to run
            models: List of model IDs to test
            variables: Variable values for prompt templating
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            ArenaRun with results from all models
        """
        start_time = time.time()

        # Render prompt with variables
        prompt_text = prompt.render(variables)
        system_prompt = prompt.render_system_prompt(variables)

        logger.info(f"Starting arena run with {len(models)} models")

        # Run all models in parallel
        tasks = [
            self._run_model(model, prompt_text, system_prompt, temperature, max_tokens)
            for model in models
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        model_results: dict[str, ModelResult] = {}
        for model, result in zip(models, results):
            if isinstance(result, Exception):
                logger.error(f"Model {model} failed: {result}")
                model_results[model] = ModelResult(
                    model_id=model,
                    response="",
                    latency_ms=0,
                    input_tokens=0,
                    output_tokens=0,
                    error=str(result),
                )
            else:
                model_results[model] = result

        # Calculate totals
        total_latency = int((time.time() - start_time) * 1000)
        total_cost = sum(
            r.cost_usd for r in model_results.values()
            if r.cost_usd is not None
        ) or None

        # Run judgments
        judgments = await self._judge_all(prompt, model_results)

        run = ArenaRun(
            id=generate_uuid(),
            prompt_id=prompt.id,
            prompt_text=prompt_text,
            system_prompt=system_prompt,
            models=models,
            results=model_results,
            judgments=judgments,
            variables=variables,
            created_at=datetime.utcnow(),
            total_latency_ms=total_latency,
            total_cost_usd=total_cost,
        )

        logger.info(
            f"Arena run complete: {len(model_results)} results, "
            f"winner: {run.get_winner()}, "
            f"latency: {total_latency}ms"
        )

        return run

    async def _run_model(
        self,
        model: str,
        prompt_text: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> ModelResult:
        """Run a single model and return result."""
        provider = self.registry.get_provider_for_model(model)

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        try:
            response: ModelResponse = await provider.complete(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return ModelResult(
                model_id=model,
                response=response.content,
                latency_ms=response.latency_ms,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
            )
        except ProviderError as e:
            logger.error(f"Provider error for {model}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {model}: {e}")
            raise

    async def _judge_all(
        self,
        prompt: ArenaPrompt,
        results: dict[str, ModelResult],
    ) -> dict[str, JudgmentResult]:
        """Judge all model responses."""
        # Use effective judge (resolves template references)
        judge_config = prompt.get_effective_judge()

        # Skip judging for models that errored
        valid_results = {k: v for k, v in results.items() if not v.error}

        if not valid_results:
            return {}

        if judge_config.type == JudgeType.LLM:
            return await self._judge_with_llm(judge_config, valid_results, prompt)
        elif judge_config.type == JudgeType.CONTAINS:
            return self._judge_with_contains(judge_config, valid_results)
        elif judge_config.type == JudgeType.REGEX:
            return self._judge_with_regex(judge_config, valid_results)
        elif judge_config.type == JudgeType.EXACT:
            return self._judge_with_exact(judge_config, valid_results)
        elif judge_config.type == JudgeType.LENGTH:
            return self._judge_with_length(judge_config, valid_results)
        elif judge_config.type == JudgeType.CONSENSUS:
            return await self._judge_with_consensus(judge_config, valid_results, prompt)
        else:
            # Default to simple pass (no real judgment)
            return {
                model_id: JudgmentResult(
                    model_id=model_id,
                    score=1.0 if result.response else 0.0,
                    passed=bool(result.response),
                    reasoning="No judgment configured",
                    judge_type="none",
                )
                for model_id, result in valid_results.items()
            }

    def _judge_with_contains(
        self,
        config: Any,
        results: dict[str, ModelResult],
    ) -> dict[str, JudgmentResult]:
        """Judge responses by checking if they contain specific text."""
        judgments = {}
        pattern = config.pattern or ""
        case_sensitive = config.case_sensitive

        for model_id, result in results.items():
            response = result.response
            search_pattern = pattern

            if not case_sensitive:
                response = response.lower()
                search_pattern = pattern.lower()

            found = search_pattern in response
            score = 1.0 if found else 0.0
            passed = score >= config.pass_threshold

            judgments[model_id] = JudgmentResult(
                model_id=model_id,
                score=score,
                passed=passed,
                reasoning=f"Contains '{pattern}': {found}",
                judge_type="contains",
            )

        return judgments

    def _judge_with_regex(
        self,
        config: Any,
        results: dict[str, ModelResult],
    ) -> dict[str, JudgmentResult]:
        """Judge responses by matching against a regex pattern."""
        import re

        judgments = {}
        pattern = config.pattern or ".*"
        flags = 0 if config.case_sensitive else re.IGNORECASE

        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            # Return all failures if pattern is invalid
            return {
                model_id: JudgmentResult(
                    model_id=model_id,
                    score=0.0,
                    passed=False,
                    reasoning=f"Invalid regex: {e}",
                    judge_type="regex",
                )
                for model_id in results.keys()
            }

        for model_id, result in results.items():
            match = compiled.search(result.response)
            score = 1.0 if match else 0.0
            passed = score >= config.pass_threshold

            judgments[model_id] = JudgmentResult(
                model_id=model_id,
                score=score,
                passed=passed,
                reasoning=f"Regex match: {bool(match)}",
                judge_type="regex",
            )

        return judgments

    def _judge_with_exact(
        self,
        config: Any,
        results: dict[str, ModelResult],
    ) -> dict[str, JudgmentResult]:
        """Judge responses by exact match (after normalization)."""
        judgments = {}
        expected = config.pattern or ""

        # Normalize: strip whitespace, optionally lowercase
        def normalize(text: str) -> str:
            text = text.strip()
            if not config.case_sensitive:
                text = text.lower()
            return text

        expected_normalized = normalize(expected)

        for model_id, result in results.items():
            response_normalized = normalize(result.response)
            match = response_normalized == expected_normalized
            score = 1.0 if match else 0.0
            passed = score >= config.pass_threshold

            judgments[model_id] = JudgmentResult(
                model_id=model_id,
                score=score,
                passed=passed,
                reasoning=f"Exact match: {match}",
                judge_type="exact",
            )

        return judgments

    def _judge_with_length(
        self,
        config: Any,
        results: dict[str, ModelResult],
    ) -> dict[str, JudgmentResult]:
        """Judge responses by length constraints."""
        judgments = {}
        min_len = config.min_length
        max_len = config.max_length

        for model_id, result in results.items():
            length = len(result.response)
            reasons = []

            # Check constraints
            passes_min = min_len is None or length >= min_len
            passes_max = max_len is None or length <= max_len

            if not passes_min:
                reasons.append(f"too short ({length} < {min_len})")
            if not passes_max:
                reasons.append(f"too long ({length} > {max_len})")

            passed = passes_min and passes_max
            score = 1.0 if passed else 0.0

            reasoning = f"Length: {length} chars"
            if reasons:
                reasoning += f" - {', '.join(reasons)}"

            judgments[model_id] = JudgmentResult(
                model_id=model_id,
                score=score,
                passed=passed,
                reasoning=reasoning,
                judge_type="length",
            )

        return judgments

    async def _judge_with_llm(
        self,
        config: Any,
        results: dict[str, ModelResult],
        prompt: ArenaPrompt,
    ) -> dict[str, JudgmentResult]:
        """Judge responses using LLM-as-a-judge."""
        judge_model = config.model or "gpt-4o"
        rubric = config.rubric or "Score the response from 0.0 to 1.0 based on quality."

        judgments = {}

        # Get provider for judge model
        try:
            provider = self.registry.get_provider_for_model(judge_model)
        except ProviderError:
            # Fall back to any available provider
            provider = next(iter(self.registry.providers.values()), None)
            if not provider:
                logger.error("No provider available for LLM judging")
                return {}

        # Judge each response
        tasks = []
        model_ids = []
        for model_id, result in results.items():
            judge_prompt = f"""You are evaluating an AI model's response.

ORIGINAL PROMPT:
{prompt.text}

MODEL RESPONSE ({model_id}):
{result.response}

EVALUATION RUBRIC:
{rubric}

Evaluate the response and provide your assessment in this exact JSON format:
{{"score": <0.0-1.0>, "passed": <true/false>, "reasoning": "<brief explanation>"}}

Respond with ONLY the JSON, no other text."""

            tasks.append(
                provider.complete(
                    model=judge_model,
                    messages=[{"role": "user", "content": judge_prompt}],
                    temperature=0.1,  # Low temp for consistent judging
                    max_tokens=500,
                )
            )
            model_ids.append(model_id)

        # Run all judge calls in parallel
        judge_responses = await asyncio.gather(*tasks, return_exceptions=True)

        for model_id, response in zip(model_ids, judge_responses):
            if isinstance(response, Exception):
                logger.error(f"LLM judge error for {model_id}: {response}")
                judgments[model_id] = JudgmentResult(
                    model_id=model_id,
                    score=0.5,
                    passed=True,
                    reasoning=f"Judge error: {response}",
                    judge_type="llm",
                )
                continue

            try:
                import json
                # Parse JSON from response
                content = response.content.strip()
                # Handle markdown code blocks
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                data = json.loads(content)
                judgments[model_id] = JudgmentResult(
                    model_id=model_id,
                    score=float(data.get("score", 0.5)),
                    passed=bool(data.get("passed", True)),
                    reasoning=str(data.get("reasoning", "No reasoning provided")),
                    judge_type="llm",
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse judge response for {model_id}: {e}")
                judgments[model_id] = JudgmentResult(
                    model_id=model_id,
                    score=0.5,
                    passed=True,
                    reasoning=f"Parse error: {response.content[:100]}...",
                    judge_type="llm",
                )

        return judgments

    async def _judge_with_consensus(
        self,
        config: Any,
        results: dict[str, ModelResult],
        prompt: ArenaPrompt,
    ) -> dict[str, JudgmentResult]:
        """Judge using consensus from multiple models."""
        voters = config.voters or ["gpt-4o", "claude-3-opus", "gemini-pro"]

        # For each response, get votes from all voter models
        judgments = {}

        for model_id, result in results.items():
            votes: list[float] = []
            reasonings: list[str] = []

            for voter in voters:
                try:
                    provider = self.registry.get_provider_for_model(voter)
                    vote_prompt = f"""Rate this AI response on a scale of 0.0 to 1.0.

PROMPT: {prompt.text}

RESPONSE: {result.response}

Respond with ONLY a number between 0.0 and 1.0."""

                    response = await provider.complete(
                        model=voter,
                        messages=[{"role": "user", "content": vote_prompt}],
                        temperature=0.1,
                        max_tokens=50,
                    )

                    # Parse score
                    import re
                    match = re.search(r"(\d+\.?\d*)", response.content)
                    if match:
                        score = min(1.0, max(0.0, float(match.group(1))))
                        votes.append(score)
                        reasonings.append(f"{voter}: {score:.2f}")
                except Exception as e:
                    logger.warning(f"Voter {voter} failed: {e}")
                    continue

            if votes:
                avg_score = sum(votes) / len(votes)
                judgments[model_id] = JudgmentResult(
                    model_id=model_id,
                    score=avg_score,
                    passed=avg_score >= 0.5,
                    reasoning=f"Consensus ({len(votes)} votes): {', '.join(reasonings)}",
                    judge_type="consensus",
                )
            else:
                judgments[model_id] = JudgmentResult(
                    model_id=model_id,
                    score=0.5,
                    passed=True,
                    reasoning="No votes received",
                    judge_type="consensus",
                )

        return judgments
