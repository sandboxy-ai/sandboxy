"""Agent listing routes."""

import logging

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sandboxy.local.context import get_local_context

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentResponse(BaseModel):
    """Response model for an agent."""

    id: str
    name: str
    model: str
    description: str | None = None
    provider: str | None = None


class AgentListResponse(BaseModel):
    """Response model for agent listing."""

    agents: list[AgentResponse]
    count: int


def _load_agents() -> list[AgentResponse]:
    """Load agents from YAML files in the local agents directory."""
    ctx = get_local_context()
    if not ctx:
        return []

    agents = []
    agent_dir = ctx.agents_dir

    if not agent_dir.exists():
        return agents

    for path in agent_dir.glob("*.y*ml"):
        try:
            content = path.read_text()
            data = yaml.safe_load(content)
            if data and isinstance(data, dict):
                agent_id = data.get("id", path.stem)
                model = data.get("model", "unknown")

                # Determine provider from model name
                provider = None
                if "gpt" in model.lower():
                    provider = "openai"
                elif "claude" in model.lower():
                    provider = "anthropic"
                elif "llama" in model.lower() or "mistral" in model.lower():
                    provider = "local"

                agents.append(
                    AgentResponse(
                        id=agent_id,
                        name=data.get("name", agent_id),
                        model=model,
                        description=data.get("description"),
                        provider=provider,
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to load agent from {path}: {e}")
            continue

    return agents


@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    """List all available agents."""
    agents = _load_agents()
    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get an agent by ID."""
    agents = _load_agents()
    for agent in agents:
        if agent.id == agent_id:
            return agent

    raise HTTPException(status_code=404, detail="Agent not found")
