"""API routes for Auto-Sim feature."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from sandboxy.autosim.runner import AutoSimConfig, AutoSimRun, AutoSimRunner, RunProgress
from sandboxy.autosim.scenarios import (
    build_config_from_scenario,
    get_events_for_scenario,
    get_personalities_for_scenario,
    list_scenarios,
    load_scenario,
)
from sandboxy.providers import get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autosim", tags=["autosim"])

# In-memory storage for runs (would use database in production)
_runs: dict[str, AutoSimRun] = {}
_active_runs: dict[str, asyncio.Task] = {}


class RunRequest(BaseModel):
    """Request to start an auto-sim run."""

    scenario: str = Field(..., description="Scenario ID to run")
    models: list[str] = Field(..., description="Models to compare")
    turns: int | None = Field(None, description="Number of turns (overrides scenario default)")
    seed: int | None = Field(None, description="Random seed for reproducibility")
    counterparty_type: str | None = Field(None, description="Counterparty type: scripted or llm")
    counterparty_personality: str | None = Field(None, description="Counterparty personality ID")
    events_mode: str | None = Field(None, description="Events mode: random, scheduled, none")
    events_probability: float | None = Field(None, description="Event probability per turn")


class RunResponse(BaseModel):
    """Response from starting a run."""

    run_id: str
    status: str
    stream_url: str


class ScenarioSummary(BaseModel):
    """Summary of a scenario."""

    id: str
    name: str
    description: str


class PersonalitySummary(BaseModel):
    """Summary of a personality."""

    id: str
    name: str
    style: str
    patience: int


class EventSummary(BaseModel):
    """Summary of an event."""

    id: str
    message: str
    probability: float
    effects: list[str]


@router.get("/scenarios", response_model=list[ScenarioSummary])
async def get_scenarios() -> list[dict[str, Any]]:
    """List all available scenarios."""
    return list_scenarios()


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict[str, Any]:
    """Get details for a specific scenario."""
    try:
        scenario = load_scenario(scenario_id)
        return {
            "id": scenario.get("id", scenario_id),
            "name": scenario.get("name", scenario_id),
            "description": scenario.get("description", ""),
            "defaults": scenario.get("defaults", {}),
            "personalities": get_personalities_for_scenario(scenario_id),
            "events": get_events_for_scenario(scenario_id),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.get("/scenarios/{scenario_id}/personalities", response_model=list[PersonalitySummary])
async def get_scenario_personalities(scenario_id: str) -> list[dict[str, Any]]:
    """Get personalities for a scenario."""
    try:
        return get_personalities_for_scenario(scenario_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.get("/scenarios/{scenario_id}/events", response_model=list[EventSummary])
async def get_scenario_events(scenario_id: str) -> list[dict[str, Any]]:
    """Get events for a scenario."""
    try:
        return get_events_for_scenario(scenario_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.post("/run", response_model=RunResponse)
async def start_run(request: RunRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Start an auto-sim run.

    The run executes in the background. Use the stream endpoint
    to get real-time progress updates.
    """
    try:
        # Build config from scenario
        config = build_config_from_scenario(
            scenario_id=request.scenario,
            models=request.models,
            seed=request.seed,
            turns=request.turns,
            counterparty_personality=request.counterparty_personality,
            counterparty_type=request.counterparty_type,
            events_mode=request.events_mode,
            events_probability=request.events_probability,
        )

        # Create runner
        runner = AutoSimRunner()

        # Start run in background
        run_id = str(uuid.uuid4())

        async def execute_run():
            try:
                run = await runner.run(config)
                run.id = run_id
                _runs[run_id] = run
            except Exception as e:
                logger.error(f"Run {run_id} failed: {e}")
                # Store error
                _runs[run_id] = AutoSimRun(
                    id=run_id,
                    config=config,
                    results={},
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                )

        # Schedule background task
        task = asyncio.create_task(execute_run())
        _active_runs[run_id] = task

        return {
            "run_id": run_id,
            "status": "running",
            "stream_url": f"/api/v1/autosim/run/{run_id}/stream",
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Get the current status/results of a run."""
    if run_id in _runs:
        return _runs[run_id].to_dict()

    if run_id in _active_runs:
        task = _active_runs[run_id]
        if task.done():
            # Task completed but not stored - check for exception
            try:
                task.result()
            except Exception as e:
                return {
                    "run_id": run_id,
                    "status": "error",
                    "error": str(e),
                }

        return {
            "run_id": run_id,
            "status": "running",
        }

    raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@router.get("/run/{run_id}/stream")
async def stream_run(run_id: str):
    """Stream progress updates for a run using Server-Sent Events."""

    async def event_generator():
        # Check if run exists
        if run_id not in _active_runs and run_id not in _runs:
            yield {
                "event": "error",
                "data": '{"error": "Run not found"}',
            }
            return

        # Poll for completion
        while True:
            if run_id in _runs:
                # Run completed
                run = _runs[run_id]
                yield {
                    "event": "completed",
                    "data": str(run.to_dict()).replace("'", '"'),  # Quick JSON conversion
                }
                return

            if run_id in _active_runs:
                task = _active_runs[run_id]
                if task.done():
                    try:
                        task.result()
                    except Exception as e:
                        yield {
                            "event": "error",
                            "data": f'{{"error": "{str(e)}"}}',
                        }
                        return

            # Still running
            yield {
                "event": "progress",
                "data": f'{{"run_id": "{run_id}", "status": "running"}}',
            }

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/run/{run_id}/results")
async def get_run_results(run_id: str) -> dict[str, Any]:
    """Get final results for a completed run."""
    if run_id not in _runs:
        # Check if still running
        if run_id in _active_runs:
            raise HTTPException(status_code=202, detail="Run still in progress")
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    run = _runs[run_id]

    return {
        "run_id": run.id,
        "scenario": run.config.scenario,
        "results": [r.to_dict() for r in run.results.values()],
        "winner": run.winner,
        "comparison": run.comparison,
    }


@router.delete("/run/{run_id}")
async def cancel_run(run_id: str) -> dict[str, str]:
    """Cancel a running auto-sim."""
    if run_id in _active_runs:
        task = _active_runs[run_id]
        if not task.done():
            task.cancel()
        del _active_runs[run_id]
        return {"status": "cancelled"}

    if run_id in _runs:
        del _runs[run_id]
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@router.get("/runs")
async def list_runs(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """List recent runs."""
    all_runs = list(_runs.values())
    all_runs.sort(key=lambda r: r.started_at, reverse=True)

    return {
        "runs": [
            {
                "id": r.id,
                "scenario": r.config.scenario,
                "models": r.config.models,
                "winner": r.winner,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in all_runs[offset:offset + limit]
        ],
        "total": len(all_runs),
    }
