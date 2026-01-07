"""Arena challenge definitions and templates.

Challenges are the core unit of Arena - structured prompts with judging criteria.
They can be defined in YAML files (challenges/*.yml) or created via the API.

Key concepts:
- Challenges: Prompts with variables and judging criteria
- Judge Templates: Reusable evaluation prompts (judges are prompts too!)
- Both support {{variable}} syntax for templating
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default directories
CHALLENGES_DIR = Path(__file__).parent.parent.parent / "challenges"
JUDGES_DIR = Path(__file__).parent.parent.parent / "judges"

# User-configurable directories (set via env vars)
USER_CHALLENGES_DIR = os.getenv("SANDBOXY_CHALLENGES_DIR")
USER_JUDGES_DIR = os.getenv("SANDBOXY_JUDGES_DIR")


class PromptCategory(str, Enum):
    """Categories for arena challenges."""

    PHILOSOPHICAL = "philosophical"
    LOGIC = "logic"
    PERSONALITY = "personality"
    ADVERSARIAL = "adversarial"
    CREATIVE = "creative"
    GAME_THEORY = "game_theory"
    CAPABILITY = "capability"
    EDUCATIONAL = "educational"
    CUSTOM = "custom"


class JudgeType(str, Enum):
    """Types of judges for evaluating responses."""

    LLM = "llm"  # LLM-as-a-judge
    CONTAINS = "contains"  # Check if response contains specific text
    REGEX = "regex"  # Match response against regex pattern
    EXACT = "exact"  # Exact match (after normalization)
    LENGTH = "length"  # Check response length constraints
    CONSENSUS = "consensus"  # Multiple models vote
    COMPUTED = "computed"  # Use helper to compute correct answer


@dataclass
class JudgeConfig:
    """Configuration for how to judge responses."""

    type: JudgeType
    # For LLM judge
    model: str | None = None  # Judge model (e.g., "openai/gpt-4o-mini")
    rubric: str | None = None  # Evaluation rubric
    # For contains/regex/exact judges
    pattern: str | None = None  # Text to match or regex pattern
    case_sensitive: bool = False  # Whether matching is case-sensitive
    # For length judge
    min_length: int | None = None  # Minimum response length (chars)
    max_length: int | None = None  # Maximum response length (chars)
    # For consensus judge
    voters: list[str] | None = None  # Models that vote
    # For computed judge
    helper: str | None = None  # Helper ID (e.g., "suitcase_tracker")
    # General
    pass_threshold: float = 0.5  # Score needed to pass

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "model": self.model,
            "rubric": self.rubric,
            "pattern": self.pattern,
            "case_sensitive": self.case_sensitive,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "pass_threshold": self.pass_threshold,
            "voters": self.voters,
            "helper": self.helper,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeConfig":
        """Create from dictionary."""
        return cls(
            type=JudgeType(data.get("type", "llm")),
            model=data.get("model"),
            rubric=data.get("rubric"),
            pattern=data.get("pattern"),
            case_sensitive=data.get("case_sensitive", False),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            pass_threshold=data.get("pass_threshold", 0.5),
            voters=data.get("voters"),
            helper=data.get("helper"),
        )


@dataclass
class JudgeTemplate:
    """A reusable judge template.

    Judges are prompts too! This allows creating and sharing evaluation
    criteria that can be reused across challenges.

    For LLM judges, the rubric supports these variables:
    - {{response}}: The model's response being judged
    - {{prompt}}: The original challenge prompt
    - {{model_id}}: The ID of the model being judged

    Example YAML:
        id: quality-judge
        name: Quality Judge
        type: llm
        model: openai/gpt-4o-mini
        rubric: |
          Rate the quality of this response on a scale of 0.0 to 1.0.

          PROMPT: {{prompt}}
          RESPONSE: {{response}}

          Consider: clarity, accuracy, helpfulness.
        pass_threshold: 0.6
    """

    id: str
    name: str
    type: JudgeType = JudgeType.LLM
    description: str | None = None
    # LLM judge fields
    model: str | None = None
    rubric: str | None = None
    # Non-LLM judge fields
    pattern: str | None = None
    case_sensitive: bool = False
    min_length: int | None = None
    max_length: int | None = None
    voters: list[str] | None = None
    # Scoring
    pass_threshold: float = 0.5

    def to_judge_config(self) -> JudgeConfig:
        """Convert to JudgeConfig for use in arena runs."""
        return JudgeConfig(
            type=self.type,
            model=self.model,
            rubric=self.rubric,
            pattern=self.pattern,
            case_sensitive=self.case_sensitive,
            min_length=self.min_length,
            max_length=self.max_length,
            pass_threshold=self.pass_threshold,
            voters=self.voters,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "model": self.model,
            "rubric": self.rubric,
            "pattern": self.pattern,
            "case_sensitive": self.case_sensitive,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "pass_threshold": self.pass_threshold,
            "voters": self.voters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeTemplate":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            type=JudgeType(data.get("type", "llm")),
            description=data.get("description"),
            model=data.get("model"),
            rubric=data.get("rubric"),
            pattern=data.get("pattern"),
            case_sensitive=data.get("case_sensitive", False),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            pass_threshold=data.get("pass_threshold", 0.5),
            voters=data.get("voters"),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "JudgeTemplate":
        """Load judge template from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class PromptVariable:
    """A variable that can be customized in a challenge."""

    name: str
    description: str | None = None
    default: Any = None
    type: str = "string"  # string, number, boolean, select
    options: list[str] | None = None  # For select type


@dataclass
class ArenaPrompt:
    """A challenge template for arena runs.

    Challenges can include variables using {{variable_name}} syntax,
    which are rendered before sending to models.

    Judging can be configured in two ways:
    1. Inline judge config (judge field)
    2. Reference to a judge template (judge_template_id field)
    """

    text: str
    id: str | None = None
    title: str | None = None
    category: PromptCategory = PromptCategory.CUSTOM
    system_prompt: str | None = None
    judge: JudgeConfig = field(default_factory=lambda: JudgeConfig(type=JudgeType.LLM))
    judge_template_id: str | None = None  # Reference to a reusable judge template
    variables: list[PromptVariable] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def get_effective_judge(self) -> JudgeConfig:
        """Get the effective judge config, resolving template references."""
        if self.judge_template_id:
            template = get_judge_template(self.judge_template_id)
            if template:
                return template.to_judge_config()
        return self.judge

    def render(self, values: dict[str, Any] | None = None) -> str:
        """Render prompt with variable substitution.

        Args:
            values: Variable values to substitute. Uses defaults for missing.

        Returns:
            Rendered prompt text
        """
        text = self.text
        values = values or {}

        # Build value map with defaults
        value_map: dict[str, Any] = {}
        for var in self.variables:
            value_map[var.name] = values.get(var.name, var.default)

        # Also include any extra values passed
        value_map.update(values)

        # Substitute {{variable}} patterns
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in value_map:
                return str(value_map[var_name])
            return match.group(0)  # Keep original if not found

        text = re.sub(r"\{\{(\w+)\}\}", replace_var, text)
        return text

    def render_system_prompt(self, values: dict[str, Any] | None = None) -> str | None:
        """Render system prompt with variable substitution."""
        if not self.system_prompt:
            return None

        values = values or {}
        text = self.system_prompt

        # Build value map with defaults
        value_map: dict[str, Any] = {}
        for var in self.variables:
            value_map[var.name] = values.get(var.name, var.default)
        value_map.update(values)

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name in value_map:
                return str(value_map[var_name])
            return match.group(0)

        text = re.sub(r"\{\{(\w+)\}\}", replace_var, text)
        return text

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "category": self.category.value,
            "system_prompt": self.system_prompt,
            "judge": self.judge.to_dict(),
            "judge_template_id": self.judge_template_id,
            "variables": [
                {
                    "name": v.name,
                    "description": v.description,
                    "default": v.default,
                    "type": v.type,
                    "options": v.options,
                }
                for v in self.variables
            ],
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArenaPrompt":
        """Create from dictionary (API or YAML)."""
        variables = [
            PromptVariable(
                name=v["name"],
                description=v.get("description"),
                default=v.get("default"),
                type=v.get("type", "string"),
                options=v.get("options"),
            )
            for v in data.get("variables", [])
        ]

        judge_data = data.get("judge", {})
        judge = JudgeConfig.from_dict(judge_data) if judge_data else JudgeConfig(type=JudgeType.LLM)

        # Handle 'prompt' key as alias for 'text' (YAML uses 'prompt')
        text = data.get("text") or data.get("prompt", "")

        return cls(
            id=data.get("id"),
            title=data.get("title"),
            text=text,
            category=PromptCategory(data.get("category", "custom")),
            system_prompt=data.get("system_prompt"),
            judge=judge,
            judge_template_id=data.get("judge_template") or data.get("judge_template_id"),
            variables=variables,
            tags=data.get("tags", []),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "ArenaPrompt":
        """Load challenge from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


# =============================================================================
# Challenge Loading
# =============================================================================

# Cache for loaded challenges
_challenges_cache: dict[str, ArenaPrompt] | None = None


def load_challenges_from_directory(directory: Path | None = None) -> dict[str, ArenaPrompt]:
    """Load all challenges from a directory of YAML files.

    Args:
        directory: Path to challenges directory. Defaults to challenges/

    Returns:
        Dictionary mapping challenge ID to ArenaPrompt
    """
    directory = directory or CHALLENGES_DIR
    challenges: dict[str, ArenaPrompt] = {}

    if not directory.exists():
        logger.warning(f"Challenges directory not found: {directory}")
        return challenges

    for path in directory.glob("*.yml"):
        try:
            challenge = ArenaPrompt.from_yaml(path)
            if challenge.id:
                challenges[challenge.id] = challenge
                logger.debug(f"Loaded challenge: {challenge.id} from {path.name}")
            else:
                logger.warning(f"Challenge in {path.name} missing 'id' field")
        except Exception as e:
            logger.error(f"Failed to load challenge from {path.name}: {e}")

    logger.info(f"Loaded {len(challenges)} challenges from {directory}")
    return challenges


def get_challenges() -> dict[str, ArenaPrompt]:
    """Get all available challenges (cached).

    Loads from:
    1. Built-in challenges/ directory
    2. User-configured SANDBOXY_CHALLENGES_DIR

    Returns:
        Dictionary mapping challenge ID to ArenaPrompt
    """
    global _challenges_cache
    if _challenges_cache is None:
        _challenges_cache = {}

        # Load built-in challenges
        _challenges_cache.update(load_challenges_from_directory(CHALLENGES_DIR))

        # Load user challenges (override built-in with same ID)
        if USER_CHALLENGES_DIR:
            user_dir = Path(USER_CHALLENGES_DIR)
            _challenges_cache.update(load_challenges_from_directory(user_dir))

    return _challenges_cache


def reload_challenges() -> dict[str, ArenaPrompt]:
    """Reload challenges from disk (clears cache).

    Returns:
        Dictionary mapping challenge ID to ArenaPrompt
    """
    global _challenges_cache
    _challenges_cache = load_challenges_from_directory()
    return _challenges_cache


def get_challenge(challenge_id: str) -> ArenaPrompt | None:
    """Get a specific challenge by ID.

    Args:
        challenge_id: Challenge identifier

    Returns:
        ArenaPrompt or None if not found
    """
    return get_challenges().get(challenge_id)


def list_challenges() -> list[ArenaPrompt]:
    """List all available challenges.

    Returns:
        List of ArenaPrompt objects
    """
    return list(get_challenges().values())


# Legacy aliases for backwards compatibility
def get_builtin_prompt(prompt_id: str) -> ArenaPrompt | None:
    """Get a challenge by ID (legacy alias)."""
    return get_challenge(prompt_id)


def list_builtin_prompts() -> list[ArenaPrompt]:
    """List all challenges (legacy alias)."""
    return list_challenges()


# =============================================================================
# Judge Template Loading
# =============================================================================

# Cache for loaded judge templates
_judges_cache: dict[str, JudgeTemplate] | None = None


def load_judges_from_directory(directory: Path | None = None) -> dict[str, JudgeTemplate]:
    """Load all judge templates from a directory of YAML files.

    Args:
        directory: Path to judges directory. Defaults to judges/

    Returns:
        Dictionary mapping judge ID to JudgeTemplate
    """
    directory = directory or JUDGES_DIR
    judges: dict[str, JudgeTemplate] = {}

    if not directory.exists():
        logger.debug(f"Judges directory not found: {directory}")
        return judges

    for path in directory.glob("*.yml"):
        try:
            judge = JudgeTemplate.from_yaml(path)
            judges[judge.id] = judge
            logger.debug(f"Loaded judge template: {judge.id} from {path.name}")
        except Exception as e:
            logger.error(f"Failed to load judge template from {path.name}: {e}")

    logger.info(f"Loaded {len(judges)} judge templates from {directory}")
    return judges


def get_judge_templates() -> dict[str, JudgeTemplate]:
    """Get all available judge templates (cached).

    Loads from:
    1. Built-in judges/ directory
    2. User-configured SANDBOXY_JUDGES_DIR

    Returns:
        Dictionary mapping judge ID to JudgeTemplate
    """
    global _judges_cache
    if _judges_cache is None:
        _judges_cache = {}

        # Load built-in judges
        _judges_cache.update(load_judges_from_directory(JUDGES_DIR))

        # Load user judges (override built-in with same ID)
        if USER_JUDGES_DIR:
            user_dir = Path(USER_JUDGES_DIR)
            _judges_cache.update(load_judges_from_directory(user_dir))

    return _judges_cache


def reload_judge_templates() -> dict[str, JudgeTemplate]:
    """Reload judge templates from disk (clears cache).

    Returns:
        Dictionary mapping judge ID to JudgeTemplate
    """
    global _judges_cache
    _judges_cache = None
    return get_judge_templates()


def get_judge_template(judge_id: str) -> JudgeTemplate | None:
    """Get a specific judge template by ID.

    Args:
        judge_id: Judge template identifier

    Returns:
        JudgeTemplate or None if not found
    """
    return get_judge_templates().get(judge_id)


def list_judge_templates() -> list[JudgeTemplate]:
    """List all available judge templates.

    Returns:
        List of JudgeTemplate objects
    """
    return list(get_judge_templates().values())
