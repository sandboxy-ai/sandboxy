"""MCP (Model Context Protocol) integration for Sandboxy.

This module provides support for connecting to real MCP servers and using
their tools alongside YAML mock tools in scenarios.

Supports two transport types:
- stdio: Local servers run as subprocesses (e.g., npx, python scripts)
- HTTP: Remote servers accessed via SSE or Streamable HTTP
"""

from sandboxy.mcp.client import (
    McpManager,
    McpServerConfig,
    inspect_mcp_server,
    inspect_mcp_server_http,
)
from sandboxy.mcp.wrapper import McpToolWrapper

__all__ = [
    "McpManager",
    "McpServerConfig",
    "McpToolWrapper",
    "inspect_mcp_server",
    "inspect_mcp_server_http",
]
