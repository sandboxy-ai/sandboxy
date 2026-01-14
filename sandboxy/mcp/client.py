"""MCP client manager - handles connections to MCP servers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

from sandboxy.mcp.wrapper import McpToolWrapper

logger = logging.getLogger(__name__)


@dataclass
class McpConnection:
    """An active connection to an MCP server."""

    name: str
    session: Any  # ClientSession
    tools: dict[str, McpToolWrapper] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio", "sse", or "streamable_http"
    _read_stream: Any = None
    _write_stream: Any = None
    _context: Any = None  # For HTTP transports


class McpServerConfig(BaseModel):
    """Configuration for an MCP server.

    Supports two modes:
    - Local (stdio): Set `command` and optionally `args`/`env`
    - Remote (HTTP): Set `url` and optionally `headers`
    """

    name: str

    # Local server (stdio transport)
    command: str | None = None
    args: list[str] = []
    env: dict[str, str] = {}

    # Remote server (HTTP transport)
    url: str | None = None
    headers: dict[str, str] = {}
    transport: Literal["auto", "stdio", "sse", "streamable_http"] = "auto"

    def is_http(self) -> bool:
        """Check if this config uses HTTP transport."""
        if self.transport in ("sse", "streamable_http"):
            return True
        if self.transport == "stdio":
            return False
        # Auto-detect: if url is set, use HTTP
        return self.url is not None


class McpManager:
    """Manages connections to multiple MCP servers."""

    def __init__(self) -> None:
        """Initialize the MCP manager."""
        self._connections: dict[str, McpConnection] = {}

    async def connect(self, config: McpServerConfig) -> McpConnection:
        """Connect to an MCP server.

        Args:
            config: Server configuration

        Returns:
            Active connection with discovered tools
        """
        if config.is_http():
            return await self._connect_http(config)
        return await self._connect_stdio(config)

    async def _connect_stdio(self, config: McpServerConfig) -> McpConnection:
        """Connect to a local MCP server via stdio."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        if not config.command:
            raise ValueError(f"Server '{config.name}' requires 'command' for stdio transport")

        # Build environment with current env + overrides
        env = os.environ.copy()
        for key, value in config.env.items():
            # Support ${VAR} expansion
            if value.startswith("${") and value.endswith("}"):
                env_key = value[2:-1]
                env[key] = os.environ.get(env_key, "")
            else:
                env[key] = value

        # Create server parameters
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=env,
        )

        # Connect to server
        read_stream, write_stream = await stdio_client(server_params).__aenter__()
        session = await ClientSession(read_stream, write_stream).__aenter__()

        # Initialize the session
        await session.initialize()

        # Discover tools
        tools_result = await session.list_tools()
        tools: dict[str, McpToolWrapper] = {}

        for tool_info in tools_result.tools:
            wrapper = McpToolWrapper(session, tool_info)
            tools[tool_info.name] = wrapper

        # Create and store connection
        connection = McpConnection(
            name=config.name,
            session=session,
            tools=tools,
            transport="stdio",
            _read_stream=read_stream,
            _write_stream=write_stream,
        )
        self._connections[config.name] = connection

        return connection

    async def _connect_http(self, config: McpServerConfig) -> McpConnection:
        """Connect to a remote MCP server via HTTP (SSE or Streamable HTTP)."""
        from mcp import ClientSession

        if not config.url:
            raise ValueError(f"Server '{config.name}' requires 'url' for HTTP transport")

        # Determine transport type
        transport = config.transport
        if transport == "auto":
            # Auto-detect based on URL path
            if config.url.endswith("/sse"):
                transport = "sse"
            else:
                transport = "streamable_http"

        # Build headers
        headers = dict(config.headers)

        if transport == "sse":
            from mcp.client.sse import sse_client

            # Connect via SSE
            context = sse_client(config.url, headers=headers if headers else None)
            read_stream, write_stream = await context.__aenter__()
        else:
            from mcp.client.streamable_http import streamablehttp_client

            # Connect via Streamable HTTP
            context = streamablehttp_client(config.url, headers=headers if headers else None)
            read_stream, write_stream, _ = await context.__aenter__()

        session = await ClientSession(read_stream, write_stream).__aenter__()

        # Initialize the session
        await session.initialize()

        # Discover tools
        tools_result = await session.list_tools()
        tools: dict[str, McpToolWrapper] = {}

        for tool_info in tools_result.tools:
            wrapper = McpToolWrapper(session, tool_info)
            tools[tool_info.name] = wrapper

        # Create and store connection
        connection = McpConnection(
            name=config.name,
            session=session,
            tools=tools,
            transport=transport,
            _read_stream=read_stream,
            _write_stream=write_stream,
            _context=context,
        )
        self._connections[config.name] = connection

        return connection

    async def connect_all(
        self,
        configs: list[McpServerConfig],
    ) -> dict[str, McpToolWrapper]:
        """Connect to multiple MCP servers and return all tools.

        Args:
            configs: List of server configurations

        Returns:
            Dictionary of tool name to wrapper (tools from all servers)
        """
        all_tools: dict[str, McpToolWrapper] = {}

        for config in configs:
            try:
                connection = await self.connect(config)
                # Prefix tool names with server name to avoid conflicts
                for tool_name, wrapper in connection.tools.items():
                    # Use unprefixed name if unique, otherwise prefix
                    if tool_name in all_tools:
                        all_tools[f"{config.name}.{tool_name}"] = wrapper
                    else:
                        all_tools[tool_name] = wrapper
            except Exception as e:
                # Log error but continue with other servers
                logger.warning("Failed to connect to MCP server '%s': %s", config.name, e)

        return all_tools

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for connection in self._connections.values():
            try:
                if connection.session:
                    await connection.session.__aexit__(None, None, None)
                if connection._context:
                    await connection._context.__aexit__(None, None, None)
            except Exception:
                logger.debug(
                    "Error during disconnect from MCP server '%s' (ignored)",
                    connection.name,
                    exc_info=True,
                )

        self._connections.clear()

    def get_all_tools(self) -> dict[str, McpToolWrapper]:
        """Get all tools from all connected servers."""
        all_tools: dict[str, McpToolWrapper] = {}
        for connection in self._connections.values():
            all_tools.update(connection.tools)
        return all_tools


def _extract_tools_info(tools_result: Any) -> list[dict[str, Any]]:
    """Extract tool information from MCP tools result."""
    tools_info: list[dict[str, Any]] = []

    for tool in tools_result.tools:
        info: dict[str, Any] = {
            "name": tool.name,
            "description": tool.description or "",
        }

        # Parse input schema for parameters
        if tool.inputSchema:
            schema = tool.inputSchema
            if isinstance(schema, dict):
                props = schema.get("properties", {})
                required = schema.get("required", [])

                params = []
                for name, prop in props.items():
                    param_info = {
                        "name": name,
                        "type": prop.get("type", "any"),
                        "required": name in required,
                        "description": prop.get("description", ""),
                    }
                    params.append(param_info)

                info["parameters"] = params
            else:
                info["parameters"] = []
        else:
            info["parameters"] = []

        tools_info.append(info)

    return tools_info


async def inspect_mcp_server(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Inspect a local MCP server (stdio) and return its available tools.

    Args:
        command: Command to start the server
        args: Command arguments
        env: Environment variables

    Returns:
        List of tool information dictionaries
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Build environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    server_params = StdioServerParameters(
        command=command,
        args=args or [],
        env=full_env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return _extract_tools_info(tools_result)


async def inspect_mcp_server_http(
    url: str,
    headers: dict[str, str] | None = None,
    transport: Literal["auto", "sse", "streamable_http"] = "auto",
) -> list[dict[str, Any]]:
    """Inspect a remote MCP server (HTTP) and return its available tools.

    Args:
        url: Server URL (e.g., "https://example.com/mcp" or "https://example.com/sse")
        headers: Optional HTTP headers (e.g., for authentication)
        transport: Transport type ("auto", "sse", or "streamable_http")

    Returns:
        List of tool information dictionaries
    """
    from mcp import ClientSession

    # Auto-detect transport based on URL
    if transport == "auto":
        if url.endswith("/sse"):
            transport = "sse"
        else:
            transport = "streamable_http"

    if transport == "sse":
        from mcp.client.sse import sse_client

        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return _extract_tools_info(tools_result)
    else:
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return _extract_tools_info(tools_result)
