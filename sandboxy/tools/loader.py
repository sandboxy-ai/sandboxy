"""Tool loader - dynamically loads tool implementations from specs."""

import importlib
from pathlib import Path
from typing import Any

import yaml

from sandboxy.core.state import EnvConfig
from sandboxy.tools.base import BaseTool, Tool, ToolConfig

# Default directories to search for tool specs
TOOLS_DIRS = [
    Path("tools/core"),
    Path("tools/community"),
]

# Built-in tool mappings (type -> module:class)
BUILTIN_TOOLS: dict[str, str] = {
    "mock_shopify": "sandboxy.tools.mock_shopify:MockShopifyTool",
    "mock_browser": "sandboxy.tools.mock_browser:MockBrowserTool",
    "mock_email": "sandboxy.tools.mock_email:MockEmailTool",
}


def _load_tool_specs(dirs: list[Path] | None = None) -> dict[str, dict[str, Any]]:
    """Load tool specifications from YAML files.

    Args:
        dirs: Directories to search for tool specs. Uses TOOLS_DIRS if None.

    Returns:
        Dictionary mapping tool type to spec.
    """
    if dirs is None:
        dirs = TOOLS_DIRS

    specs: dict[str, dict[str, Any]] = {}
    for d in dirs:
        if not d.exists():
            continue
        for path in d.glob("**/*.yaml"):
            try:
                raw = yaml.safe_load(path.read_text())
                if raw and "type" in raw:
                    specs[raw["type"]] = raw
            except yaml.YAMLError:
                continue
        for path in d.glob("**/*.yml"):
            try:
                raw = yaml.safe_load(path.read_text())
                if raw and "type" in raw:
                    specs[raw["type"]] = raw
            except yaml.YAMLError:
                continue

    return specs


def _load_tool_class(module_path: str) -> type[BaseTool]:
    """Load a tool class from a module path.

    Args:
        module_path: Path in format "module.path:ClassName".

    Returns:
        Tool class.

    Raises:
        ImportError: If module cannot be imported.
        AttributeError: If class not found in module.
    """
    module_name, class_name = module_path.split(":")
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


class ToolLoader:
    """Loader for creating tool instances from environment config."""

    @classmethod
    def from_env_config(
        cls,
        env: EnvConfig,
        tool_dirs: list[Path] | None = None,
    ) -> dict[str, Tool]:
        """Create tool instances from environment configuration.

        Args:
            env: Environment configuration containing tool references.
            tool_dirs: Optional directories to search for tool specs.

        Returns:
            Dictionary mapping tool name to tool instance.

        Raises:
            ValueError: If a tool type cannot be found.
        """
        specs = _load_tool_specs(tool_dirs)
        tools: dict[str, Tool] = {}

        for tool_ref in env.tools:
            # First check built-in tools
            if tool_ref.type in BUILTIN_TOOLS:
                module_path = BUILTIN_TOOLS[tool_ref.type]
            # Then check loaded specs
            elif tool_ref.type in specs:
                spec = specs[tool_ref.type]
                if "impl" not in spec or "module" not in spec["impl"]:
                    raise ValueError(
                        f"Tool spec for '{tool_ref.type}' missing impl.module"
                    )
                module_path = spec["impl"]["module"]
            else:
                raise ValueError(f"Unknown tool type: {tool_ref.type}")

            # Load and instantiate the tool class
            tool_cls = _load_tool_class(module_path)
            config = ToolConfig(
                name=tool_ref.name,
                type=tool_ref.type,
                description=tool_ref.description,
                config=tool_ref.config,
            )
            tools[tool_ref.name] = tool_cls(config)

        return tools

    @classmethod
    def get_available_tools(cls, tool_dirs: list[Path] | None = None) -> list[str]:
        """Get list of available tool types.

        Args:
            tool_dirs: Optional directories to search for tool specs.

        Returns:
            List of available tool type names.
        """
        specs = _load_tool_specs(tool_dirs)
        available = list(BUILTIN_TOOLS.keys())
        available.extend(specs.keys())
        return sorted(set(available))
