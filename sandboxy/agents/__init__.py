"""Agents module - Agent interface, loader, and implementations."""

from sandboxy.agents.base import Agent, AgentAction, AgentConfig, AgentKind, BaseAgent
from sandboxy.agents.llm_prompt import LlmPromptAgent
from sandboxy.agents.loader import (
    AgentLoader,
    create_agent_from_config,
    create_agent_from_model,
)

__all__ = [
    "Agent",
    "AgentAction",
    "AgentConfig",
    "AgentKind",
    "AgentLoader",
    "BaseAgent",
    "LlmPromptAgent",
    "create_agent_from_config",
    "create_agent_from_model",
]
