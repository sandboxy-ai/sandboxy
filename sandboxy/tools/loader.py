"""Tool loader - dynamically loads tool implementations from specs.

This module handles:
    - Loading tool specifications from YAML files
    - Creating tool instances from environment configuration
    - Loading YAML tool libraries
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

import yaml

from sandboxy.core.state import EnvConfig
from sandboxy.tools.base import BaseTool, Tool, ToolConfig

logger = logging.getLogger(__name__)

# Default directories to search for tool specs
TOOLS_DIRS = [
    Path("tools/core"),
    Path("tools/community"),
]

# Default directories for YAML tool libraries
YAML_TOOL_DIRS = [
    Path("tools"),
    Path("sandboxy/tools/libraries"),
]


def get_tool_dirs() -> list[Path]:
    """Get tool directories, including local context if available.

    Returns:
        List of directories to search for YAML tool libraries.
    """
    from sandboxy.local.context import get_local_context, is_local_mode

    dirs: list[Path] = []

    if is_local_mode():
        ctx = get_local_context()
        if ctx and ctx.tools_dir.exists():
            dirs.append(ctx.tools_dir)

    dirs.extend(YAML_TOOL_DIRS)
    return dirs


# Built-in tool mappings (type -> module:class)
BUILTIN_TOOLS: dict[str, str] = {
    "mock_lemonade": "sandboxy.tools.mock_lemonade:MockLemonadeTool",
    "mock_store": "sandboxy.tools.mock_store:MockStoreTool",
    "mock_wedding": "sandboxy.tools.mock_wedding:MockWeddingTool",
    "mock_customer_support": "sandboxy.tools.mock_customer_support:MockCustomerSupportTool",
    "mock_mechanic": "sandboxy.tools.mock_mechanic:MockMechanicTool",
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
            except yaml.YAMLError as e:
                logger.warning("Failed to parse tool spec %s: %s", path, e)
                continue
        for path in d.glob("**/*.yml"):
            try:
                raw = yaml.safe_load(path.read_text())
                if raw and "type" in raw:
                    specs[raw["type"]] = raw
            except yaml.YAMLError as e:
                logger.warning("Failed to parse tool spec %s: %s", path, e)
                continue

    return specs


def load_tool_class(module_path: str) -> type[BaseTool]:
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
                    msg = f"Tool spec for '{tool_ref.type}' missing impl.module"
                    raise ValueError(msg)
                module_path = spec["impl"]["module"]
            else:
                msg = f"Unknown tool type: {tool_ref.type}"
                raise ValueError(msg)

            # Load and instantiate the tool class
            tool_cls = load_tool_class(module_path)
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

        # Also list YAML tool libraries
        yaml_libs = get_yaml_tool_libraries()
        available.extend(yaml_libs)

        return sorted(set(available))


# -----------------------------------------------------------------------------
# YAML Tool Library Support
# -----------------------------------------------------------------------------


def get_yaml_tool_libraries(tool_dirs: list[Path] | None = None) -> list[str]:
    """Get list of available YAML tool library names.

    Args:
        tool_dirs: Directories to search. Uses YAML_TOOL_DIRS if None.

    Returns:
        List of library names (without extension).
    """
    if tool_dirs is None:
        tool_dirs = YAML_TOOL_DIRS

    libraries: list[str] = []
    for d in tool_dirs:
        if not d.exists():
            continue
        for ext in (".yml", ".yaml"):
            for path in d.glob(f"*{ext}"):
                # Only include files that start with mock_ or have tools: key
                try:
                    raw = yaml.safe_load(path.read_text())
                    if raw and ("tools" in raw or path.stem.startswith("mock_")):
                        libraries.append(path.stem)
                except yaml.YAMLError as e:
                    logger.warning("Failed to parse tool library %s: %s", path, e)
                    continue

    return libraries


def load_yaml_tools_from_scenario(
    scenario_data: dict[str, Any],
    tool_dirs: list[Path] | None = None,
) -> dict[str, Tool]:
    """Load YAML-defined tools from a scenario definition.

    This handles both `tools_from` library references and inline `tools` definitions.
    Use this when loading scenarios that define their own tools.

    Args:
        scenario_data: Parsed scenario YAML containing tools and/or tools_from
        tool_dirs: Optional directories to search for tool libraries

    Returns:
        Dictionary of tool name to tool instance
    """
    from sandboxy.tools.yaml_tools import load_scenario_tools

    if tool_dirs is None:
        tool_dirs = YAML_TOOL_DIRS

    return load_scenario_tools(scenario_data, tool_dirs)


def load_yaml_tool_library(
    library_name: str,
    tool_dirs: list[Path] | None = None,
) -> dict[str, Tool]:
    """Load all tools from a YAML tool library.

    Args:
        library_name: Name of the library (without extension)
        tool_dirs: Optional directories to search

    Returns:
        Dictionary of tool name to tool instance
    """
    from sandboxy.tools.yaml_tools import YamlToolLoader

    if tool_dirs is None:
        tool_dirs = YAML_TOOL_DIRS

    loader = YamlToolLoader(tool_dirs)
    library = loader.load_library(library_name)
    return loader.create_tool_instances(library.tools)
