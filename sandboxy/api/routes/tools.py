"""Tool listing routes with config schemas."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from sandboxy.tools.loader import BUILTIN_TOOLS, load_tool_class
from sandboxy.tools.base import ToolConfig

router = APIRouter()


class ToolConfigField(BaseModel):
    """Schema for a single config field."""

    type: str
    label: str
    description: str | None = None
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[str] | None = None
    items: dict[str, Any] | None = None  # For array types


class ToolAction(BaseModel):
    """Schema for a tool action."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolResponse(BaseModel):
    """Response model for a tool."""

    id: str
    name: str
    description: str | None = None
    config_schema: dict[str, Any]
    actions: list[ToolAction]


class ToolListResponse(BaseModel):
    """Response model for tool listing."""

    tools: list[ToolResponse]
    count: int


def _load_tools() -> list[ToolResponse]:
    """Load tools and their schemas from the built-in tools registry."""
    tools = []

    for tool_id, tool_path in BUILTIN_TOOLS.items():
        try:
            tool_class = load_tool_class(tool_path)

            # Get config schema if available
            config_schema = {}
            if hasattr(tool_class, "config_schema"):
                config_schema = tool_class.config_schema()

            # Get actions by instantiating with minimal config
            actions = []
            try:
                # Create a minimal ToolConfig for instantiation
                minimal_config = ToolConfig(name=tool_id, type=tool_id)
                tool_instance = tool_class(minimal_config)
                if hasattr(tool_instance, "get_actions"):
                    raw_actions = tool_instance.get_actions()
                    for action in raw_actions:
                        actions.append(
                            ToolAction(
                                name=action.get("name", ""),
                                description=action.get("description", ""),
                                parameters=action.get("parameters", {}),
                            )
                        )
            except Exception:
                # If instantiation fails, skip actions
                pass

            tools.append(
                ToolResponse(
                    id=tool_id,
                    name=tool_class.__name__,
                    description=tool_class.__doc__,
                    config_schema=config_schema,
                    actions=actions,
                )
            )
        except Exception:
            # Skip tools that fail to load
            continue

    return tools


@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List all available tools with their config schemas and actions."""
    tools = _load_tools()
    return ToolListResponse(tools=tools, count=len(tools))


@router.get("/tools/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: str):
    """Get a specific tool by ID."""
    tools = _load_tools()
    for tool in tools:
        if tool.id == tool_id:
            return tool

    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
