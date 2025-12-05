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


class SessionExport(BaseModel):
    """Full export of a session for replay/sharing."""

    session_id: str
    module_id: str
    module_name: str | None
    agent_id: str
    variables: dict | None
    state: str
    created_at: str
    completed_at: str | None
    duration_seconds: float | None
    events: list[dict]
    evaluation: dict | None
    summary: dict


@router.get("/sessions/{session_id}/export", response_model=SessionExport)
async def export_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Export a session as JSON for replay or sharing.

    Returns a complete record of the session including:
    - Session metadata
    - All events in order
    - Evaluation results
    - Summary statistics
    """
    session = await crud.get_session_by_id(db, session_id, include_events=True)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get module name
    module = await crud.get_module_by_id(db, session.module_id)
    module_name = module.name if module else None

    # Format events
    events = [
        {
            "sequence": e.sequence,
            "type": e.event_type,
            "payload": e.payload,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
        }
        for e in session.events
    ] if session.events else []

    # Format evaluation
    evaluation = None
    if session.evaluation:
        evaluation = {
            "score": session.evaluation.score,
            "checks": session.evaluation.checks,
        }

    # Calculate duration
    duration = None
    if session.started_at and session.completed_at:
        duration = (session.completed_at - session.started_at).total_seconds()

    # Build summary
    message_events = [e for e in events if e["type"] in ("user", "agent")]
    tool_events = [e for e in events if e["type"] == "tool_call"]

    summary = {
        "total_events": len(events),
        "user_messages": len([e for e in events if e["type"] == "user"]),
        "agent_messages": len([e for e in events if e["type"] == "agent"]),
        "tool_calls": len(tool_events),
        "final_score": evaluation["score"] if evaluation else None,
    }

    return SessionExport(
        session_id=session.id,
        module_id=session.module_id,
        module_name=module_name,
        agent_id=session.agent_id,
        variables=session.variables,
        state=session.state,
        created_at=session.created_at.isoformat() if session.created_at else "",
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        duration_seconds=duration,
        events=events,
        evaluation=evaluation,
        summary=summary,
    )


class ShareableResult(BaseModel):
    """Shareable result for social media."""

    title: str
    description: str
    score: float | None
    score_display: str
    share_url: str
    embed_code: str


@router.get("/sessions/{session_id}/share", response_model=ShareableResult)
async def get_shareable_result(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a shareable result summary for social media.

    Returns formatted text and links suitable for sharing.
    """
    session = await crud.get_session_by_id(db, session_id, include_events=True)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    module = await crud.get_module_by_id(db, session.module_id)
    module_name = module.name if module else "Unknown Scenario"

    # Get score
    score = session.evaluation.score if session.evaluation else None
    if score is not None:
        if score >= 0.8:
            score_display = f"🏆 {score:.0%} - Excellent!"
        elif score >= 0.6:
            score_display = f"✅ {score:.0%} - Good"
        elif score >= 0.4:
            score_display = f"⚠️ {score:.0%} - Needs Improvement"
        else:
            score_display = f"❌ {score:.0%} - Failed"
    else:
        score_display = "No score available"

    # Build shareable content
    title = f"I just played {module_name} on Sandboxy!"
    description = f"Score: {score_display}\nAgent: {session.agent_id}"

    # Placeholder URLs - would be real in production
    share_url = f"https://sandboxy.ai/replay/{session_id}"
    embed_code = f'<iframe src="{share_url}/embed" width="600" height="400"></iframe>'

    return ShareableResult(
        title=title,
        description=description,
        score=score,
        score_display=score_display,
        share_url=share_url,
        embed_code=embed_code,
    )
