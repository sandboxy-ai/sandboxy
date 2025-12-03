"""Agent listing routes."""

from pathlib import Path

import yaml
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Paths to agent YAML directories
AGENT_DIRS = [
    Path(__file__).parent.parent.parent.parent / "agents" / "core",
    Path(__file__).parent.parent.parent.parent / "agents" / "community",
]


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
    """Load agents from YAML files in the agent directories."""
    agents = []

    for agent_dir in AGENT_DIRS:
        if not agent_dir.exists():
            continue

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
            except Exception:
                # Skip invalid files
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

    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Agent not found")
