"""Agent loader - loads agent configurations and instantiates agents."""

import logging
from pathlib import Path
from typing import Any

import yaml

from sandboxy.agents.base import Agent, AgentConfig
from sandboxy.agents.llm_prompt import LlmPromptAgent

logger = logging.getLogger(__name__)

# Default directories to search for agent specs (user's directories only)
DEFAULT_AGENT_DIRS = [
    Path.home() / ".sandboxy" / "agents",
]


def get_agent_dirs() -> list[Path]:
    """Get agent directories, including local if in local mode.

    Returns:
        List of directories to search for agents.
    """
    from sandboxy.local.context import get_local_context, is_local_mode

    dirs: list[Path] = []

    if is_local_mode():
        ctx = get_local_context()
        if ctx and ctx.agents_dir.exists():
            dirs.append(ctx.agents_dir)

    dirs.extend(DEFAULT_AGENT_DIRS)
    return dirs


class AgentLoader:
    """Loader for agent configurations and instantiation."""

    def __init__(self, dirs: list[Path] | None = None) -> None:
        """Initialize loader with directories to search.

        Args:
            dirs: Directories to search for agent specs. Uses defaults if None.
        """
        self.dirs = dirs if dirs is not None else DEFAULT_AGENT_DIRS
        self._configs: dict[str, AgentConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load all agent configurations from directories."""
        for d in self.dirs:
            if not d.exists():
                continue

            for path in d.glob("**/*.yaml"):
                self._load_config_file(path)
            for path in d.glob("**/*.yml"):
                self._load_config_file(path)

    def _load_config_file(self, path: Path) -> None:
        """Load a single agent configuration file."""
        try:
            raw: dict[str, Any] = yaml.safe_load(path.read_text())
            if not raw or "id" not in raw:
                logger.debug("Skipping %s: missing 'id' field", path)
                return

            config = AgentConfig(
                id=raw["id"],
                name=raw.get("name", raw["id"]),
                kind=raw.get("kind", "llm-prompt"),
                model=raw.get("model", ""),
                system_prompt=raw.get("system_prompt", ""),
                tools=raw.get("tools", []),
                params=raw.get("params", {}),
                impl=raw.get("impl", {}),
            )
            self._configs[config.id] = config
            logger.debug("Loaded agent config: %s from %s", config.id, path)
        except yaml.YAMLError as e:
            logger.warning("Failed to parse YAML file %s: %s", path, e)
        except KeyError as e:
            logger.warning("Missing required field in %s: %s", path, e)

    def list_ids(self) -> list[str]:
        """Get list of available agent IDs.

        Returns:
            List of agent IDs.
        """
        return list(self._configs.keys())

    def get_config(self, agent_id: str) -> AgentConfig | None:
        """Get agent configuration by ID.

        Args:
            agent_id: Agent identifier.

        Returns:
            Agent configuration or None if not found.
        """
        return self._configs.get(agent_id)

    def load(self, agent_id: str) -> Agent:
        """Load and instantiate an agent by ID.

        Args:
            agent_id: Agent identifier. Can be either:
                - A predefined agent ID from user's YAML files
                - A model ID (e.g., "openai/gpt-4o", "anthropic/claude-3.5-haiku")

        Returns:
            Instantiated agent.

        Raises:
            ValueError: If agent ID not found.
        """
        config = self._configs.get(agent_id)
        if config is None:
            # Check if it's a model ID (contains a /)
            if "/" in agent_id:
                # Create a dynamic agent config for this model
                config = AgentConfig(
                    id=agent_id,
                    name=agent_id.split("/")[-1].replace("-", " ").title(),
                    kind="llm-prompt",
                    model=agent_id,
                    system_prompt="You are a helpful assistant. Use the available tools to complete tasks.",
                    tools=[],
                    params={"temperature": 0.7, "max_tokens": 2048},
                    impl={},
                )
            else:
                msg = f"Agent not found: {agent_id}"
                raise ValueError(msg)
        return self._instantiate(config)

    def load_default(self) -> Agent:
        """Load the default agent.

        Returns:
            Default agent instance.

        Raises:
            ValueError: If no agents are available and no model specified.
        """
        # Use any available agent from user's config
        if self._configs:
            config = next(iter(self._configs.values()))
            return self._instantiate(config)

        raise ValueError("No agents available. Specify a model with -m (e.g., -m openai/gpt-4o)")

    def _instantiate(self, config: AgentConfig) -> Agent:
        """Create agent instance from configuration.

        Args:
            config: Agent configuration.

        Returns:
            Agent instance.

        Raises:
            ValueError: If agent kind is not supported.
        """
        return _instantiate_agent(config)


def _instantiate_agent(config: AgentConfig) -> Agent:
    """Create agent instance from configuration.

    Args:
        config: Agent configuration.

    Returns:
        Agent instance.

    Raises:
        ValueError: If agent kind is not supported.
    """
    if config.kind == "llm-prompt":
        return LlmPromptAgent(config)
    msg = f"Unsupported agent kind: {config.kind}"
    raise ValueError(msg)


def create_agent_from_config(config: AgentConfig) -> Agent:
    """Create an agent instance directly from configuration.

    Args:
        config: Agent configuration.

    Returns:
        Agent instance.
    """
    return _instantiate_agent(config)


def create_agent_from_model(model_id: str, system_prompt: str = "") -> Agent:
    """Create an agent directly from a model ID.

    Args:
        model_id: Model identifier (e.g., "openai/gpt-4o", "anthropic/claude-3.5-sonnet")
        system_prompt: Optional system prompt override.

    Returns:
        Agent instance configured for the model.
    """
    config = AgentConfig(
        id=model_id,
        name=model_id.split("/")[-1].replace("-", " ").title() if "/" in model_id else model_id,
        kind="llm-prompt",
        model=model_id,
        system_prompt=system_prompt or "You are a helpful assistant.",
        tools=[],
        params={"temperature": 0.7, "max_tokens": 4096},
        impl={},
    )
    return _instantiate_agent(config)
