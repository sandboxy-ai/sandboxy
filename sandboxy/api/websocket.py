"""WebSocket handler for interactive sessions."""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sandboxy.agents.loader import AgentLoader
from sandboxy.core.mdl_parser import apply_variables, load_module
from sandboxy.session.manager import session_manager

router = APIRouter()

# Agent directories
AGENT_DIRS = [
    Path(__file__).parent.parent.parent / "agents" / "core",
    Path(__file__).parent.parent.parent / "agents" / "community",
]

# Module directory
MODULES_DIR = Path(__file__).parent.parent.parent / "modules"


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and track a WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict[str, Any]):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


def _load_module_from_id(module_id: str):
    """Load a module from ID (either file:slug or database ID)."""
    if module_id.startswith("file:"):
        slug = module_id[5:]
        for ext in [".yml", ".yaml"]:
            path = MODULES_DIR / f"{slug}{ext}"
            if path.exists():
                return load_module(path)
        raise ValueError(f"Module file not found: {slug}")
    else:
        # Try loading by slug from files
        for ext in [".yml", ".yaml"]:
            path = MODULES_DIR / f"{module_id}{ext}"
            if path.exists():
                return load_module(path)
        raise ValueError(f"Module not found: {module_id}")


@router.websocket("/ws/session")
async def websocket_session(websocket: WebSocket):
    """WebSocket endpoint for interactive sessions.

    Protocol:
        Client -> Server:
            {"type": "start", "module_id": "...", "agent_id": "...", "variables": {...}}
            {"type": "message", "content": "..."}
            {"type": "pause"}
            {"type": "resume"}

        Server -> Client:
            {"type": "started", "session_id": "..."}
            {"type": "event", "event_type": "user|agent|tool_call|...", "payload": {...}}
            {"type": "awaiting_input", "prompt": "..."}
            {"type": "completed", "evaluation": {...}}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()
    session_id: str | None = None
    event_task: asyncio.Task | None = None

    async def send_events(session_id: str, event_queue: asyncio.Queue):
        """Background task to send events to the WebSocket."""
        try:
            while True:
                event = await event_queue.get()

                if event.type == "awaiting_input":
                    await websocket.send_json({
                        "type": "awaiting_input",
                        "session_id": session_id,
                        "prompt": event.payload.get("prompt", ""),
                        "timeout": event.payload.get("timeout"),
                    })
                elif event.type == "completed":
                    await websocket.send_json({
                        "type": "completed",
                        "session_id": session_id,
                        "evaluation": event.payload.get("evaluation"),
                    })
                    break  # Session complete
                elif event.type == "error":
                    await websocket.send_json({
                        "type": "error",
                        "session_id": session_id,
                        "message": event.payload.get("message", "Unknown error"),
                    })
                    break  # Session ended with error
                else:
                    await websocket.send_json({
                        "type": "event",
                        "session_id": session_id,
                        "event_type": event.type,
                        "payload": event.payload,
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                await websocket.send_json({
                    "type": "error",
                    "session_id": session_id,
                    "message": f"Event streaming error: {e}",
                })
            except Exception:
                pass

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "start":
                # Start a new session
                module_id = message.get("module_id")
                agent_id = message.get("agent_id", "gpt5-nano")
                variables = message.get("variables", {})

                if not module_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "module_id is required",
                    })
                    continue

                try:
                    # Load module
                    module = _load_module_from_id(module_id)

                    # Apply variables
                    module = apply_variables(module, variables)

                    # Load agent
                    loader = AgentLoader(AGENT_DIRS)
                    agent = loader.load(agent_id)

                    # Apply module's agent_config overrides
                    if module.agent_config:
                        if "system_prompt" in module.agent_config:
                            agent.config.system_prompt = module.agent_config["system_prompt"]

                    # Create session
                    session = session_manager.create_session(module, agent, variables)
                    session_id = session.id

                    # Track connection
                    manager.active_connections[session_id] = websocket

                    await websocket.send_json({
                        "type": "started",
                        "session_id": session_id,
                        "module_name": module.id,
                        "agent_id": agent_id,
                    })

                    # Start session and event streaming
                    event_queue = await session_manager.start_session(session_id)
                    event_task = asyncio.create_task(send_events(session_id, event_queue))

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to start session: {e}",
                    })

            elif msg_type == "message":
                # User sent a message
                if not session_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active session. Send 'start' first.",
                    })
                    continue

                content = message.get("content", "")

                try:
                    session_manager.provide_input(session_id, content)
                except RuntimeError as e:
                    await websocket.send_json({
                        "type": "error",
                        "session_id": session_id,
                        "message": str(e),
                    })

            elif msg_type == "pause":
                if session_id:
                    session_manager.pause_session(session_id)
                    await websocket.send_json({
                        "type": "paused",
                        "session_id": session_id,
                    })

            elif msg_type == "resume":
                if session_id:
                    session_manager.resume_session(session_id)
                    await websocket.send_json({
                        "type": "resumed",
                        "session_id": session_id,
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError:
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON",
            })
        except Exception:
            pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        # Cleanup
        if event_task and not event_task.done():
            event_task.cancel()
        if session_id:
            manager.disconnect(session_id)
            session_manager.delete_session(session_id)
