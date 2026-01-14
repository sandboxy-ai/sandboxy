"""Local development context manager.

This module provides the LocalContext class for managing local development
configurations in Sandboxy. It handles path resolution, file discovery,
and environment variable overrides for containerized deployments.
"""

from __future__ import annotations

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Global context - set when running in local mode
_local_context: LocalContext | None = None


@dataclass
class LocalContext:
    """Configuration for local development mode.

    Manages paths and discovery for a local Sandboxy project.
    """

    root_dir: Path
    scenarios_dir: Path = field(init=False)
    tools_dir: Path = field(init=False)
    agents_dir: Path = field(init=False)
    runs_dir: Path = field(init=False)
    datasets_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        """Initialize derived paths from root directory."""
        # Support env var overrides for containerization
        self.scenarios_dir = Path(
            os.environ.get("SANDBOXY_SCENARIOS_DIR", self.root_dir / "scenarios")
        )
        self.tools_dir = Path(os.environ.get("SANDBOXY_TOOLS_DIR", self.root_dir / "tools"))
        self.agents_dir = Path(os.environ.get("SANDBOXY_AGENTS_DIR", self.root_dir / "agents"))
        self.runs_dir = Path(os.environ.get("SANDBOXY_RUNS_DIR", self.root_dir / "runs"))
        self.datasets_dir = Path(
            os.environ.get("SANDBOXY_DATASETS_DIR", self.root_dir / "datasets")
        )

    def discover(self) -> dict[str, list[dict[str, Any]]]:
        """Discover all local files (YAML and Python tools).

        Returns:
            Dictionary with scenarios, tools, and agents lists.

        """
        # Tools include both YAML and Python files
        tools = self._list_yaml_files(self.tools_dir)
        tools.extend(self._list_python_tools(self.tools_dir))

        return {
            "scenarios": self._list_yaml_files(self.scenarios_dir),
            "tools": tools,
            "agents": self._list_yaml_files(self.agents_dir),
        }

    def _list_yaml_files(self, directory: Path) -> list[dict[str, Any]]:
        """List YAML files with basic metadata.

        Args:
            directory: Directory to scan for YAML files.

        Returns:
            List of file metadata dictionaries.

        """
        files = []
        if not directory.exists():
            return files

        for path in directory.glob("**/*.yaml"):
            files.append(self._parse_yaml_metadata(path))
        for path in directory.glob("**/*.yml"):
            files.append(self._parse_yaml_metadata(path))

        # Sort by name
        files.sort(key=lambda x: x.get("name", x.get("id", "")))
        return files

    def _parse_yaml_metadata(self, path: Path) -> dict[str, Any]:
        """Parse basic metadata from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Dictionary with file metadata.

        """
        try:
            content = yaml.safe_load(path.read_text())
            if not isinstance(content, dict):
                content = {}
        except Exception as e:
            logger.warning("Failed to parse %s: %s", path, e)
            content = {}

        return {
            "id": content.get("id", path.stem),
            "name": content.get("name", path.stem),
            "description": content.get("description", ""),
            "type": content.get("type"),
            "path": str(path),
            "relative_path": str(path.relative_to(self.root_dir)),
        }

    def _list_python_tools(self, directory: Path) -> list[dict[str, Any]]:
        """List Python tool files with metadata.

        Scans for .py files that contain BaseTool subclasses.

        Args:
            directory: Directory to scan for Python files.

        Returns:
            List of file metadata dictionaries.

        """
        files = []
        if not directory.exists():
            return files

        for path in directory.glob("*.py"):
            # Skip dunder files
            if path.name.startswith("_"):
                continue

            try:
                source = path.read_text()
                tree = ast.parse(source)

                # Find classes that might be BaseTool subclasses
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if it inherits from BaseTool
                        for base in node.bases:
                            base_name = ""
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                base_name = base.attr

                            if base_name == "BaseTool":
                                # Convert class name to snake_case for tool type
                                class_name = node.name
                                s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", class_name)
                                tool_type = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

                                # Extract docstring
                                docstring = ast.get_docstring(node) or ""
                                description = docstring.split("\n")[0] if docstring else ""

                                files.append(
                                    {
                                        "id": tool_type,
                                        "name": class_name,
                                        "description": description,
                                        "type": "python",
                                        "path": str(path),
                                        "relative_path": str(path.relative_to(self.root_dir)),
                                    }
                                )
                                break  # Only add once per file

            except Exception as e:
                logger.warning("Failed to parse Python tool %s: %s", path, e)
                continue

        files.sort(key=lambda x: x.get("name", x.get("id", "")))
        return files

    def ensure_directories(self) -> list[Path]:
        """Ensure all standard directories exist.

        Returns:
            List of created directories.

        """
        created = []
        for directory in [
            self.scenarios_dir,
            self.tools_dir,
            self.agents_dir,
            self.runs_dir,
            self.datasets_dir,
        ]:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created.append(directory)
                logger.info("Created directory: %s", directory)
        return created


def get_local_context() -> LocalContext | None:
    """Get the current local context.

    Returns:
        The active LocalContext or None if not in local mode.

    """
    return _local_context


def set_local_context(ctx: LocalContext | None) -> None:
    """Set the local context.

    Args:
        ctx: LocalContext to set, or None to clear.

    """
    global _local_context
    _local_context = ctx


def is_local_mode() -> bool:
    """Check if running in local mode.

    Returns:
        True if a local context is active.

    """
    return _local_context is not None
