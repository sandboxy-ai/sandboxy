"""Session management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sandboxy.db import crud
from sandboxy.db.database import get_db

router = APIRouter()


class SessionEventResponse(BaseModel):
    """Response model for a session event."""

    id: int
    sequence: int
    event_type: str
    payload: dict

    class Config:
        from_attributes = True


class EvaluationResponse(BaseModel):
    """Response model for an evaluation."""

    id: str
    score: float | None
    checks: dict | None

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Response model for a session."""

    id: str
    module_id: str
    agent_id: str
    variables: dict | None
    state: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    events: list[SessionEventResponse] | None = None
    evaluation: EvaluationResponse | None = None

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response model for session listing."""

    sessions: list[SessionResponse]
    count: int


class SessionCreate(BaseModel):
    """Request model for creating a session."""

    module_id: str
    agent_id: str
    variables: dict | None = None


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    module_id: str | None = None,
    limit: int = 50,
):
    """List sessions, optionally filtered by module."""
    sessions = await crud.get_sessions(db, module_id=module_id, limit=limit)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                module_id=s.module_id,
                agent_id=s.agent_id,
                variables=s.variables,
                state=s.state,
                created_at=s.created_at.isoformat() if s.created_at else "",
                started_at=s.started_at.isoformat() if s.started_at else None,
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
            )
            for s in sessions
        ],
        count=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_events: bool = True,
):
    """Get a session by ID."""
    session = await crud.get_session_by_id(db, session_id, include_events=include_events)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    events = None
    evaluation = None

    if include_events and session.events:
        events = [
            SessionEventResponse(
                id=e.id,
                sequence=e.sequence,
                event_type=e.event_type,
                payload=e.payload,
            )
            for e in session.events
        ]

    if session.evaluation:
        evaluation = EvaluationResponse(
            id=session.evaluation.id,
            score=session.evaluation.score,
            checks=session.evaluation.checks,
        )

    return SessionResponse(
        id=session.id,
        module_id=session.module_id,
        agent_id=session.agent_id,
        variables=session.variables,
        state=session.state,
        created_at=session.created_at.isoformat() if session.created_at else "",
        started_at=session.started_at.isoformat() if session.started_at else None,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        events=events,
        evaluation=evaluation,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    session: SessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new session (for REST-based, non-interactive sessions)."""
    # Note: For interactive sessions, use WebSocket at /ws/session instead
    created = await crud.create_session(
        db,
        module_id=session.module_id,
        agent_id=session.agent_id,
        variables=session.variables,
    )

    return SessionResponse(
        id=created.id,
        module_id=created.module_id,
        agent_id=created.agent_id,
        variables=created.variables,
        state=created.state,
        created_at=created.created_at.isoformat() if created.created_at else "",
        started_at=None,
        completed_at=None,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a session and its events."""
    session = await crud.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await crud.delete_session(db, session)


@router.get("/sessions/{session_id}/events", response_model=list[SessionEventResponse])
async def get_session_events(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all events for a session."""
    events = await crud.get_session_events(db, session_id)
    return [
        SessionEventResponse(
            id=e.id,
            sequence=e.sequence,
            event_type=e.event_type,
            payload=e.payload,
        )
        for e in events
    ]
