"""MCP tool wrapper - adapts MCP tools to Sandboxy's Tool protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sandboxy.tools.base import ToolResult

if TYPE_CHECKING:
    from mcp import ClientSession
    from mcp.types import Tool as McpTool


class McpToolWrapper:
    """Wraps an MCP tool to match Sandboxy's Tool protocol.

    This allows MCP tools to be used seamlessly alongside YAML mock tools
    in scenarios.
    """

    def __init__(self, session: ClientSession, tool_info: McpTool) -> None:
        """Initialize the wrapper.

        Args:
            session: Active MCP client session
            tool_info: Tool information from MCP server
        """
        self.session = session
        self.name = tool_info.name
        self.description = tool_info.description or ""
        self._input_schema = tool_info.inputSchema

    async def invoke_async(
        self,
        action: str,
        args: dict[str, Any],
        env_state: dict[str, Any],
    ) -> ToolResult:
        """Invoke the MCP tool asynchronously.

        Args:
            action: Action name (ignored for MCP tools - they're single-action)
            args: Arguments to pass to the tool
            env_state: Environment state (not used by MCP tools)

        Returns:
            ToolResult with success/error and data
        """
        try:
            result = await self.session.call_tool(self.name, args)

            # Extract content from MCP result
            # MCP tools return a list of content blocks
            if result.content:
                # Combine text content
                text_parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                    elif hasattr(block, "data"):
                        text_parts.append(str(block.data))

                data = "\n".join(text_parts) if text_parts else result.content

                if result.isError:
                    return ToolResult(success=False, error=str(data))

                return ToolResult(success=True, data=data)

            return ToolResult(success=True, data=None)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def invoke(
        self,
        action: str,
        args: dict[str, Any],
        env_state: dict[str, Any],
    ) -> ToolResult:
        """Synchronous invoke - raises error, use invoke_async instead."""
        raise RuntimeError("MCP tools must be invoked asynchronously. Use invoke_async() instead.")

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available actions with their schemas.

        MCP tools are single-action, so we return a single "call" action.
        """
        return [
            {
                "name": "call",
                "description": self.description,
                "parameters": self._input_schema
                or {
                    "type": "object",
                    "properties": {},
                },
            }
        ]
