"""Sandboxy Arena - Multi-model AI comparison and testing.

Arena allows you to:
- Run the same prompt against multiple AI models in parallel
- Judge and score responses using code, LLM, or consensus
- Generate shareable video content of the results
- Track leaderboards and model performance

Usage:
    from sandboxy.arena import ArenaRunner, ArenaPrompt

    runner = ArenaRunner()
    result = await runner.run(
        prompt=ArenaPrompt(text="What is the trolley problem?"),
        models=["openai/gpt-4o", "anthropic/claude-3-opus"],
    )
"""

from sandboxy.arena.prompts import ArenaPrompt, PromptCategory
from sandboxy.arena.runner import ArenaRunner, ArenaRun, ModelResult

__all__ = [
    "ArenaPrompt",
    "PromptCategory",
    "ArenaRunner",
    "ArenaRun",
    "ModelResult",
]
