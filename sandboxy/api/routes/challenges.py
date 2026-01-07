"""Challenge system API routes - interactive challenges where users compete against AI."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sandboxy.challenges import (
    Challenge,
    load_challenge,
    list_challenges,
    evaluate_goals,
)
from sandboxy.db import crud
from sandboxy.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class ChallengeGoalResponse(BaseModel):
    """A goal within a challenge."""

    id: str
    name: str
    description: str
    points: float
    achieved: bool = False
    points_earned: float = 0.0


class ChallengeSummary(BaseModel):
    """Summary info for challenge listing."""

    id: str
    name: str
    description: str
    category: str
    difficulty: str
    max_turns: int
    tags: list[str]


class ChallengeDetail(BaseModel):
    """Full challenge details."""

    id: str
    name: str
    description: str
    category: str
    difficulty: str
    max_turns: int
    time_limit_seconds: int | None
    tags: list[str]
    goals: list[ChallengeGoalResponse]
    scoring_info: dict


class ChallengeListResponse(BaseModel):
    """Response for listing challenges."""

    challenges: list[ChallengeSummary]
    count: int


class ChallengeStartResponse(BaseModel):
    """Response when starting a challenge."""

    session_id: str
    challenge_id: str
    challenge_name: str
    max_turns: int
    goals: list[ChallengeGoalResponse]
    message: str


class ChallengeCompleteRequest(BaseModel):
    """Request to complete/score a challenge attempt."""

    session_id: str
    player_name: str | None = None


class GoalResult(BaseModel):
    """Result for a single goal."""

    id: str
    name: str
    description: str
    achieved: bool
    points_earned: float


class ChallengeCompleteResponse(BaseModel):
    """Response with final score after completing a challenge."""

    challenge_id: str
    challenge_name: str
    session_id: str
    score: float
    max_score: float
    goals_completed: int
    goals_total: int
    goals: list[GoalResult]
    turn_bonus: float
    turns_used: int
    max_turns: int
    breakdown: dict
    player_name: str | None


# =============================================================================
# Routes
# =============================================================================


@router.get("/challenges", response_model=ChallengeListResponse)
async def get_challenges(
    category: str | None = None,
    difficulty: str | None = None,
):
    """List all available challenges.

    Optionally filter by category or difficulty.
    Only returns interactive challenges (those with goals defined).
    """
    all_challenges = list_challenges()

    # Filter for interactive challenges (those that can be loaded with goals)
    challenges = []
    for c in all_challenges:
        try:
            # Try to load the challenge to verify it has the new format
            loaded = load_challenge(c["id"])
            if loaded.goals:  # Only include challenges with goals
                challenges.append(c)
        except Exception:
            # Skip challenges that can't be parsed (old format)
            continue

    # Filter if requested
    if category:
        challenges = [c for c in challenges if c.get("category") == category]
    if difficulty:
        challenges = [c for c in challenges if c.get("difficulty") == difficulty]

    return ChallengeListResponse(
        challenges=[
            ChallengeSummary(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                category=c["category"],
                difficulty=c["difficulty"],
                max_turns=c["max_turns"],
                tags=c.get("tags", []),
            )
            for c in challenges
        ],
        count=len(challenges),
    )


@router.get("/challenges/{challenge_id}", response_model=ChallengeDetail)
async def get_challenge(challenge_id: str):
    """Get detailed information about a specific challenge."""
    try:
        challenge = load_challenge(challenge_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Challenge not found: {challenge_id}")
    except Exception as e:
        logger.warning(f"Failed to load challenge {challenge_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid challenge format: {challenge_id}")

    return ChallengeDetail(
        id=challenge.id,
        name=challenge.name,
        description=challenge.description,
        category=challenge.category,
        difficulty=challenge.difficulty,
        max_turns=challenge.max_turns,
        time_limit_seconds=challenge.time_limit_seconds,
        tags=challenge.tags,
        goals=[
            ChallengeGoalResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                points=g.points if g.points else (g.max_points or 0),
            )
            for g in challenge.goals
        ],
        scoring_info={
            "turn_bonus": challenge.turn_bonus,
            "max_turns": challenge.max_turns,
        },
    )


@router.post("/challenges/{challenge_id}/start", response_model=ChallengeStartResponse)
async def start_challenge(
    challenge_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start a new challenge attempt.

    Creates a session and returns the session ID for WebSocket connection.
    The frontend should connect to /ws/session/{session_id} to play.
    """
    try:
        challenge = load_challenge(challenge_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Challenge not found: {challenge_id}")
    except Exception as e:
        logger.warning(f"Failed to load challenge {challenge_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid challenge: {challenge_id}")

    # Get agent from challenge config or use default
    agent_id = challenge.module.agent_config.get("id", "openrouter/anthropic/claude-sonnet-4")

    # Create a session using the challenge's underlying module
    # The module_id is the challenge_id prefixed with "challenge:"
    session = await crud.create_session(
        db,
        module_id=f"challenge:{challenge_id}",
        agent_id=agent_id,
        variables={},
    )

    return ChallengeStartResponse(
        session_id=session.id,
        challenge_id=challenge.id,
        challenge_name=challenge.name,
        max_turns=challenge.max_turns,
        goals=[
            ChallengeGoalResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                points=g.points if g.points else (g.max_points or 0),
            )
            for g in challenge.goals
        ],
        message=f"Challenge started! Connect to WebSocket at /ws/session/{session.id}",
    )


@router.post("/challenges/{challenge_id}/complete", response_model=ChallengeCompleteResponse)
async def complete_challenge(
    challenge_id: str,
    request: ChallengeCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete a challenge and get the final score.

    Evaluates all goals based on the session transcript and environment state.
    """
    try:
        challenge = load_challenge(challenge_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Challenge not found: {challenge_id}")

    # Get the session
    session = await crud.get_session_by_id(db, request.session_id, include_events=True)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Extract transcript and tool calls from session events
    transcript = []
    tool_calls = []
    env_state = {}

    if session.events:
        for event in session.events:
            if event.event_type in ("user", "customer"):
                transcript.append({
                    "role": event.event_type,
                    "content": event.payload.get("content", ""),
                })
            elif event.event_type in ("agent", "assistant"):
                transcript.append({
                    "role": event.event_type,
                    "content": event.payload.get("content", ""),
                })
            elif event.event_type == "tool_call":
                tool_calls.append(event.payload)
            elif event.event_type == "env_state":
                # Merge environment state updates
                env_state.update(event.payload)

    # Count turns (user messages)
    turns_used = sum(1 for msg in transcript if msg.get("role") in ("user", "customer"))

    # Evaluate goals
    result = evaluate_goals(
        challenge=challenge,
        env_state=env_state,
        transcript=transcript,
        tool_calls=tool_calls,
        turns_used=turns_used,
    )

    # Format goal results
    goal_results = []
    for goal in challenge.goals:
        goal_results.append(
            GoalResult(
                id=goal.id,
                name=goal.name,
                description=goal.description,
                achieved=goal.achieved,
                points_earned=goal.points_earned,
            )
        )

    # Store evaluation in session (upsert to handle re-evaluation)
    await crud.upsert_evaluation(
        db,
        session_id=session.id,
        score=result["score"] / result["max_score"] if result["max_score"] > 0 else 0,
        checks={
            "challenge_id": challenge_id,
            "goals_achieved": result["goals_achieved"],
            "turn_bonus": result["turn_bonus"],
            "breakdown": result["breakdown"],
        },
    )

    return ChallengeCompleteResponse(
        challenge_id=challenge.id,
        challenge_name=challenge.name,
        session_id=request.session_id,
        score=result["score"],
        max_score=result["max_score"],
        goals_completed=result["goals_completed"],
        goals_total=result["goals_total"],
        goals=goal_results,
        turn_bonus=result["turn_bonus"],
        turns_used=result["turns_used"],
        max_turns=result["max_turns"],
        breakdown=result["breakdown"],
        player_name=request.player_name,
    )


@router.get("/challenges/{challenge_id}/attempts/{session_id}")
async def get_challenge_attempt(
    challenge_id: str,
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get details of a specific challenge attempt."""
    session = await crud.get_session_by_id(db, session_id, include_events=True)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify it's for this challenge
    if session.module_id != f"challenge:{challenge_id}":
        raise HTTPException(status_code=400, detail="Session is not for this challenge")

    # Get evaluation if exists
    evaluation = None
    if session.evaluation:
        evaluation = {
            "score": session.evaluation.score,
            "checks": session.evaluation.checks,
        }

    # Format events as transcript
    transcript = []
    if session.events:
        for event in session.events:
            if event.event_type in ("user", "customer", "agent", "assistant"):
                transcript.append({
                    "role": event.event_type,
                    "content": event.payload.get("content", ""),
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                })

    return {
        "session_id": session.id,
        "challenge_id": challenge_id,
        "state": session.state,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "transcript": transcript,
        "evaluation": evaluation,
    }
