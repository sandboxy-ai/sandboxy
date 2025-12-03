"""Agent loader - loads agent configurations and instantiates agents."""

from pathlib import Path
from typing import Any

import yaml

from sandboxy.agents.base import Agent, AgentConfig
from sandboxy.agents.llm_prompt import LlmPromptAgent

# Default directories to search for agent specs
DEFAULT_AGENT_DIRS = [
    Path("agents/core"),
    Path("agents/community"),
    Path.home() / ".sandboxy" / "agents",
]


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
        except (yaml.YAMLError, KeyError):
            # Skip invalid files
            pass

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
            agent_id: Agent identifier.

        Returns:
            Instantiated agent.

        Raises:
            ValueError: If agent ID not found.
        """
        config = self._configs.get(agent_id)
        if config is None:
            raise ValueError(f"Agent not found: {agent_id}")
        return self._instantiate(config)

    def load_default(self) -> Agent:
        """Load the default agent.

        Returns:
            Default agent instance.

        Raises:
            ValueError: If no agents are available.
        """
        # Prefer gpt35-cheap for cost efficiency
        if "sandboxy/core/gpt35-cheap" in self._configs:
            return self._instantiate(self._configs["sandboxy/core/gpt35-cheap"])

        # Then try gpt4-support
        if "sandboxy/core/gpt4-support" in self._configs:
            return self._instantiate(self._configs["sandboxy/core/gpt4-support"])

        # Fall back to any available agent
        if self._configs:
            config = next(iter(self._configs.values()))
            return self._instantiate(config)

        raise ValueError("No agents available")

    def _instantiate(self, config: AgentConfig) -> Agent:
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

        # Placeholder for other kinds
        raise ValueError(f"Unsupported agent kind: {config.kind}")


def create_agent_from_config(config: AgentConfig) -> Agent:
    """Create an agent instance directly from configuration.

    Args:
        config: Agent configuration.

    Returns:
        Agent instance.
    """
    loader = AgentLoader(dirs=[])
    return loader._instantiate(config)
