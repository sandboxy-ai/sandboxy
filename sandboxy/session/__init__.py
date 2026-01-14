"""Session management for interactive Sandboxy sessions.

This module provides session management for coordinating interactive sessions
between WebSocket connections and the AsyncRunner. It maintains in-memory
session state for local development and testing.

Typical usage:
    from sandboxy.session import SessionManager, Session

    manager = SessionManager()
    session = manager.create_session(module, agent)
    event_queue = await manager.start_session(session.id)
"""

from sandboxy.session.manager import Session, SessionManager, session_manager

__all__ = [
    "Session",
    "SessionManager",
    "session_manager",
]
