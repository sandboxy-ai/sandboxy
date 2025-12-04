"""Session Manager - coordinates interactive sessions between WebSocket and AsyncRunner."""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sandboxy.agents.base import Agent
from sandboxy.core.async_runner import AsyncRunner, RunEvent
from sandboxy.core.state import ModuleSpec, SessionState


@dataclass
class Session:
    """An active interactive session."""

    id: str
    module: ModuleSpec
    agent: Agent
    variables: dict[str, Any]
    runner: AsyncRunner
    events: list[RunEvent] = field(default_factory=list)
    _run_task: asyncio.Task | None = None
    _event_queue: asyncio.Queue[RunEvent] = field(default_factory=asyncio.Queue)

    @property
    def state(self) -> SessionState:
        """Get current session state."""
        return self.runner.session_state


class SessionManager:
    """Manages active interactive sessions.

    This is an in-memory session store. For production, you'd want to
    persist sessions to a database and potentially distribute them
    across multiple workers.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(
        self,
        module: ModuleSpec,
        agent: Agent,
        variables: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            module: Module specification to run.
            agent: Agent to use for the session.
            variables: Optional variables for the module.

        Returns:
            The created Session object.
        """
        session_id = str(uuid4())
        runner = AsyncRunner(module, agent)

        session = Session(
            id=session_id,
            module=module,
            agent=agent,
            variables=variables or {},
            runner=runner,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Returns:
            True if session was deleted, False if not found.
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Cancel running task if any
            if session._run_task and not session._run_task.done():
                session._run_task.cancel()
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[Session]:
        """List all active sessions."""
        return list(self._sessions.values())

    async def start_session(self, session_id: str) -> asyncio.Queue[RunEvent]:
        """Start running a session.

        Args:
            session_id: ID of the session to start.

        Returns:
            Queue that will receive events as they occur.

        Raises:
            ValueError: If session not found.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Start the runner in a background task
        session._run_task = asyncio.create_task(self._run_session(session))

        return session._event_queue

    async def _run_session(self, session: Session) -> None:
        """Run a session, pushing events to its queue."""
        try:
            async for event in session.runner.run():
                session.events.append(event)
                await session._event_queue.put(event)

                # If awaiting input, wait for it to be provided before continuing
                if event.type == "awaiting_input":
                    # The caller should call provide_input() which will unblock the runner
                    pass

        except asyncio.CancelledError:
            # Session was cancelled, that's fine
            pass
        except Exception as e:
            # Push error event
            error_event = RunEvent(type="error", payload={"message": str(e)})
            session.events.append(error_event)
            await session._event_queue.put(error_event)

    def provide_input(self, session_id: str, content: str) -> None:
        """Provide user input for a session.

        Args:
            session_id: ID of the session.
            content: User's input text.

        Raises:
            ValueError: If session not found.
            RuntimeError: If session is not awaiting input.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.runner.provide_input(content)

    def inject_event(
        self,
        session_id: str,
        tool_name: str,
        event_type: str,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Inject a game event into a session.

        This triggers an event in the specified tool (e.g., "heatwave" in
        the lemonade stand). The event modifies game state and returns
        a description that should be shown to the user/agent.

        Args:
            session_id: ID of the session.
            tool_name: Name of the tool to call.
            event_type: Type of event to trigger.
            args: Optional additional arguments.

        Returns:
            The event result data from the tool.

        Raises:
            ValueError: If session not found or event fails.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        return session.runner.inject_event(tool_name, event_type, args)

    def pause_session(self, session_id: str) -> bool:
        """Pause a session (not fully implemented yet)."""
        session = self.get_session(session_id)
        if not session:
            return False
        # TODO: Implement proper pause
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session (not fully implemented yet)."""
        session = self.get_session(session_id)
        if not session:
            return False
        # TODO: Implement proper resume
        return True


# Global session manager instance
session_manager = SessionManager()
