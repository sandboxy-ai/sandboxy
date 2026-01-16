"""API routes for local development mode."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sandboxy.local.context import get_local_context

router = APIRouter()
logger = logging.getLogger(__name__)


class LocalFileInfo(BaseModel):
    """Information about a local file."""

    id: str
    name: str
    description: str
    type: str | None
    path: str
    relative_path: str


class LocalStatusResponse(BaseModel):
    """Response for local status endpoint."""

    mode: str = "local"
    root_dir: str
    scenarios: list[LocalFileInfo]
    tools: list[LocalFileInfo]
    agents: list[LocalFileInfo]


class VariableInfo(BaseModel):
    """Information about a scenario variable."""

    name: str
    label: str = ""
    type: str = "string"  # string, number, boolean, select
    default: Any = None
    options: list[str] = []  # For select type
    required: bool = True


class ScenarioDetail(BaseModel):
    """Detailed scenario information."""

    id: str
    name: str
    description: str
    type: str | None
    path: str
    content: dict[str, Any]
    variables: list[VariableInfo] = []  # Detected/defined variables


@router.get("/local/status", response_model=LocalStatusResponse)
async def get_local_status() -> LocalStatusResponse:
    """Get status of local development environment.

    Returns discovered files and current configuration.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()

    return LocalStatusResponse(
        root_dir=str(ctx.root_dir),
        scenarios=[LocalFileInfo(**s) for s in discovered["scenarios"]],
        tools=[LocalFileInfo(**t) for t in discovered["tools"]],
        agents=[LocalFileInfo(**a) for a in discovered["agents"]],
    )


@router.get("/local/scenarios")
async def list_local_scenarios() -> list[LocalFileInfo]:
    """List scenarios from local scenarios/ directory."""
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()
    return [LocalFileInfo(**s) for s in discovered["scenarios"]]


def _extract_variables(content: dict[str, Any]) -> list[VariableInfo]:
    """Extract variables from scenario content.

    Variables can be:
    1. Explicitly defined in 'variables' section
    2. Detected from {var} patterns in content

    Args:
        content: Parsed scenario YAML

    Returns:
        List of detected variables
    """
    import re

    variables: dict[str, VariableInfo] = {}

    # 1. Get explicitly defined variables
    for var in content.get("variables", []):
        name = var.get("name", "")
        if name:
            variables[name] = VariableInfo(
                name=name,
                label=var.get("label", name.replace("_", " ").title()),
                type=var.get("type", "string"),
                default=var.get("default"),
                options=var.get("options", []),
                required=var.get("required", True),
            )

    # 2. Detect {var} patterns in content (only in user-facing text, not tool definitions)
    def find_vars(obj: Any, found: set[str], skip_keys: set[str] | None = None) -> None:
        if skip_keys is None:
            skip_keys = set()
        if isinstance(obj, str):
            # Skip double-brace patterns like {{name}} - these are tool param refs
            # First remove all {{...}} patterns, then find single {var}
            cleaned = re.sub(r"\{\{[^}]+\}\}", "", obj)
            # Find {variable} patterns, excluding {state.xxx} references
            matches = re.findall(r"\{(\w+)\}", cleaned)
            for match in matches:
                if not match.startswith("state"):
                    found.add(match)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                # Skip tool definitions - they have their own param syntax
                if k in skip_keys:
                    continue
                find_vars(v, found, skip_keys)
        elif isinstance(obj, list):
            for item in obj:
                find_vars(item, found, skip_keys)

    detected: set[str] = set()
    # Skip 'environment' section since it contains tool definitions with param refs
    # Also skip 'tools' which might be inline tool definitions
    skip_sections = {"environment", "tools", "config"}
    find_vars(content, detected, skip_sections)

    # Add detected variables that aren't already defined
    for name in detected:
        if name not in variables:
            variables[name] = VariableInfo(
                name=name,
                label=name.replace("_", " ").title(),
                type="string",
                default=None,
                options=[],
                required=True,
            )

    return list(variables.values())


@router.get("/local/scenarios/{scenario_id}")
async def get_local_scenario(scenario_id: str) -> ScenarioDetail:
    """Get a specific scenario by ID.

    Args:
        scenario_id: The scenario identifier.

    Returns:
        Scenario details including full YAML content and detected variables.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()

    # Find the scenario
    for s in discovered["scenarios"]:
        if s["id"] == scenario_id:
            # Load full content
            try:
                content = yaml.safe_load(Path(s["path"]).read_text())
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error loading scenario: {e}",
                ) from e

            # Extract variables
            variables = _extract_variables(content or {})

            return ScenarioDetail(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                type=s["type"],
                path=s["path"],
                content=content or {},
                variables=variables,
            )

    raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.get("/local/tools")
async def list_local_tools() -> list[LocalFileInfo]:
    """List tools from local tools/ directory."""
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()
    return [LocalFileInfo(**t) for t in discovered["tools"]]


@router.get("/local/tools/{tool_id}")
async def get_local_tool(tool_id: str) -> dict[str, Any]:
    """Get a specific tool library by ID.

    Args:
        tool_id: The tool library identifier.

    Returns:
        Tool library details including full YAML content.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()

    # Find the tool
    for t in discovered["tools"]:
        if t["id"] == tool_id:
            # Load full content
            try:
                content = yaml.safe_load(Path(t["path"]).read_text())
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error loading tool: {e}",
                ) from e

            return {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "path": t["path"],
                "content": content or {},
            }

    raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")


@router.get("/local/agents")
async def list_local_agents() -> list[LocalFileInfo]:
    """List agents from local agents/ directory."""
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()
    return [LocalFileInfo(**a) for a in discovered["agents"]]


@router.get("/local/agents/{agent_id}")
async def get_local_agent(agent_id: str) -> dict[str, Any]:
    """Get a specific agent by ID.

    Args:
        agent_id: The agent identifier.

    Returns:
        Agent details including full YAML content.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    discovered = ctx.discover()

    # Find the agent
    for a in discovered["agents"]:
        if a["id"] == agent_id:
            # Load full content
            try:
                content = yaml.safe_load(Path(a["path"]).read_text())
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error loading agent: {e}",
                ) from e

            return {
                "id": a["id"],
                "name": a["name"],
                "description": a["description"],
                "path": a["path"],
                "content": content or {},
            }

    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")


@router.get("/local/runs")
async def list_local_runs() -> list[dict[str, Any]]:
    """List run results from local runs/ directory."""
    import json

    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    runs = []
    if ctx.runs_dir.exists():
        for path in sorted(ctx.runs_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text())
                runs.append(
                    {
                        "filename": path.name,
                        "path": str(path),
                        "scenario_id": data.get("scenario_id"),
                        "timestamp": data.get("timestamp"),
                        "metadata": data.get("metadata", {}),
                    }
                )
            except Exception:
                # Skip invalid files
                continue

    return runs[:100]  # Limit to most recent 100


@router.get("/local/runs/{filename}")
async def get_local_run(filename: str) -> dict[str, Any]:
    """Get a specific run result.

    Args:
        filename: The run result filename.

    Returns:
        Full run result data.
    """
    import json

    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    filepath = ctx.runs_dir / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {filename}")

    try:
        return json.loads(filepath.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading run: {e}") from e


# =============================================================================
# Scenario Execution API
# =============================================================================


class RunScenarioRequest(BaseModel):
    """Request to run a scenario."""

    scenario_id: str
    model: str
    variables: dict[str, Any] = Field(default_factory=dict)
    max_turns: int = 20
    max_tokens: int = 1024
    temperature: float = 0.7


class RunScenarioResponse(BaseModel):
    """Response from running a scenario."""

    id: str
    scenario_id: str
    model: str
    response: str
    history: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    final_state: dict[str, Any]
    evaluation: dict[str, Any] | None
    latency_ms: int
    error: str | None


class CompareModelsRequest(BaseModel):
    """Request to compare multiple models on a scenario."""

    scenario_id: str
    models: list[str]
    runs_per_model: int = 1
    variables: dict[str, Any] = Field(default_factory=dict)
    max_turns: int = 20


class CompareModelsResponse(BaseModel):
    """Response from multi-model comparison."""

    scenario_id: str
    scenario_name: str
    models: list[str]
    runs_per_model: int
    stats: dict[str, Any]
    ranking: list[str]
    winner: str | None
    results: list[dict[str, Any]] = Field(default_factory=list)  # Individual run results


@router.post("/local/run", response_model=RunScenarioResponse)
async def run_scenario(request: RunScenarioRequest) -> RunScenarioResponse:
    """Run a scenario with a single model.

    Args:
        request: Run configuration including scenario_id, model, and variables.

    Returns:
        Scenario execution result.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find the scenario file
    discovered = ctx.discover()
    scenario_path = None

    for s in discovered["scenarios"]:
        if s["id"] == request.scenario_id:
            scenario_path = Path(s["path"])
            break

    if not scenario_path:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario not found: {request.scenario_id}",
        )

    try:
        from sandboxy.scenarios.unified import UnifiedRunner, load_unified_scenario

        spec = load_unified_scenario(scenario_path)
        runner = UnifiedRunner()

        result = await runner.run(
            scenario=spec,
            model=request.model,
            variables=request.variables,
            max_turns=request.max_turns,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Save result to runs/
        from sandboxy.local.results import save_run_result

        save_run_result(request.scenario_id, result.to_dict())

        return RunScenarioResponse(
            id=result.id,
            scenario_id=result.scenario_id,
            model=result.model,
            response=result.response,
            history=[{"role": m.role, "content": m.content} for m in result.history],
            tool_calls=[
                {"tool": tc.tool, "action": tc.action, "args": tc.args, "success": tc.success}
                for tc in result.tool_calls
            ],
            final_state=result.final_state,
            evaluation=result.evaluation.to_dict() if result.evaluation else None,
            latency_ms=result.latency_ms,
            error=result.error,
        )

    except Exception as e:
        logger.exception(f"Error running scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/local/compare", response_model=CompareModelsResponse)
async def compare_models(request: CompareModelsRequest) -> CompareModelsResponse:
    """Run a scenario with multiple models and compare results.

    Args:
        request: Comparison configuration including scenario_id, models, and runs_per_model.

    Returns:
        Comparison results with statistics and ranking.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find the scenario file
    discovered = ctx.discover()
    scenario_path = None

    for s in discovered["scenarios"]:
        if s["id"] == request.scenario_id:
            scenario_path = Path(s["path"])
            break

    if not scenario_path:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario not found: {request.scenario_id}",
        )

    if len(request.models) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least one model is required",
        )

    try:
        from sandboxy.scenarios.comparison import run_comparison
        from sandboxy.scenarios.unified import load_unified_scenario

        spec = load_unified_scenario(scenario_path)

        comparison = await run_comparison(
            scenario=spec,
            models=request.models,
            runs_per_model=request.runs_per_model,
            variables=request.variables,
            max_turns=request.max_turns,
        )

        # Save comparison result
        from sandboxy.local.results import save_run_result

        save_run_result(
            f"{request.scenario_id}_comparison",
            comparison.to_dict(),
        )

        return CompareModelsResponse(
            scenario_id=comparison.scenario_id,
            scenario_name=comparison.scenario_name,
            models=comparison.models,
            runs_per_model=comparison.runs_per_model,
            stats={k: v.to_dict() for k, v in comparison.stats.items()},
            ranking=comparison.get_ranking(),
            winner=comparison.get_winner(),
            results=[r.to_dict() for r in comparison.results],
        )

    except Exception as e:
        logger.exception(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def get_model_pricing(model_id: str) -> dict[str, float] | None:
    """Get pricing for a model from OpenRouter models."""
    from sandboxy.providers.openrouter import OPENROUTER_MODELS

    model_info = OPENROUTER_MODELS.get(model_id)
    if not model_info:
        return None
    return {
        "input": model_info.input_cost_per_million or 0,
        "output": model_info.output_cost_per_million or 0,
    }


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float | None:
    """Calculate cost in USD for a model run."""
    pricing = get_model_pricing(model_id)
    if not pricing:
        return None
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


@router.get("/local/models")
async def list_available_models() -> list[dict[str, Any]]:
    """List available models from OpenRouter."""
    from sandboxy.providers.openrouter import OPENROUTER_MODELS

    models = []
    for model_id, info in OPENROUTER_MODELS.items():
        # Format price string
        if info.input_cost_per_million == 0 and info.output_cost_per_million == 0:
            price = "Free"
        else:
            price = f"${info.input_cost_per_million:.2f}/${info.output_cost_per_million:.2f}"

        models.append(
            {
                "id": model_id,
                "name": info.name,
                "price": price,
                "pricing": {
                    "input": info.input_cost_per_million or 0,
                    "output": info.output_cost_per_million or 0,
                },
                "provider": info.provider,
                "context_length": info.context_length,
                "supports_vision": info.supports_vision,
            }
        )

    return models


# =============================================================================
# Scenario Management API
# =============================================================================


class SaveScenarioRequest(BaseModel):
    """Request to save a scenario."""

    id: str
    content: str  # YAML content


class SaveScenarioResponse(BaseModel):
    """Response from saving a scenario."""

    id: str
    path: str
    message: str


@router.post("/local/scenarios", response_model=SaveScenarioResponse)
async def save_scenario(request: SaveScenarioRequest) -> SaveScenarioResponse:
    """Save a new scenario to the scenarios/ directory.

    Args:
        request: Scenario ID and YAML content.

    Returns:
        Saved scenario info.
    """
    import re

    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Validate ID
    if not request.id:
        raise HTTPException(status_code=400, detail="Scenario ID is required")

    if not re.match(r"^[a-z0-9-]+$", request.id):
        raise HTTPException(
            status_code=400,
            detail="Scenario ID must contain only lowercase letters, numbers, and hyphens",
        )

    # Validate YAML
    try:
        yaml.safe_load(request.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e

    # Ensure scenarios directory exists
    ctx.scenarios_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    filepath = ctx.scenarios_dir / f"{request.id}.yml"
    filepath.write_text(request.content)

    return SaveScenarioResponse(
        id=request.id,
        path=str(filepath),
        message=f"Scenario saved to {filepath}",
    )


@router.put("/local/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    request: SaveScenarioRequest,
) -> SaveScenarioResponse:
    """Update an existing scenario.

    Args:
        scenario_id: The scenario ID to update.
        request: New YAML content.

    Returns:
        Updated scenario info.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find existing file
    filepath = ctx.scenarios_dir / f"{scenario_id}.yml"
    if not filepath.exists():
        filepath = ctx.scenarios_dir / f"{scenario_id}.yaml"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")

    # Validate YAML
    try:
        yaml.safe_load(request.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e

    # Update file
    filepath.write_text(request.content)

    return SaveScenarioResponse(
        id=scenario_id,
        path=str(filepath),
        message=f"Scenario updated at {filepath}",
    )


@router.delete("/local/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str) -> dict[str, str]:
    """Delete a scenario.

    Args:
        scenario_id: The scenario ID to delete.

    Returns:
        Confirmation message.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find existing file
    filepath = ctx.scenarios_dir / f"{scenario_id}.yml"
    if not filepath.exists():
        filepath = ctx.scenarios_dir / f"{scenario_id}.yaml"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")

    filepath.unlink()

    return {"message": f"Scenario {scenario_id} deleted"}


# =============================================================================
# Tool Management
# =============================================================================


class SaveToolRequest(BaseModel):
    """Request to save a tool."""

    name: str
    toolType: str = "yaml"  # yaml, python, or mcp
    content: str  # YAML or Python content


class SaveToolResponse(BaseModel):
    """Response from saving a tool."""

    name: str
    path: str
    message: str


@router.post("/local/tools", response_model=SaveToolResponse)
async def save_tool(request: SaveToolRequest) -> SaveToolResponse:
    """Save a new tool to the tools/ directory.

    Supports three tool types:
    - yaml: Declarative YAML mock tools
    - python: Python tool class (generates .py file)
    - mcp: MCP server configuration (YAML with type: mcp)

    Args:
        request: Tool name, type, and content.

    Returns:
        Saved tool info.
    """
    import re

    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Validate name
    if not request.name:
        raise HTTPException(status_code=400, detail="Tool name is required")

    if not re.match(r"^[a-z0-9_]+$", request.name):
        raise HTTPException(
            status_code=400,
            detail="Tool name must contain only lowercase letters, numbers, and underscores",
        )

    # Ensure tools directory exists
    ctx.tools_dir.mkdir(parents=True, exist_ok=True)

    # Handle different tool types
    if request.toolType == "python":
        # Save as Python file
        filepath = ctx.tools_dir / f"{request.name}.py"
        filepath.write_text(request.content)
    elif request.toolType == "mcp":
        # Validate YAML for MCP config
        try:
            yaml.safe_load(request.content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e
        filepath = ctx.tools_dir / f"{request.name}.yml"
        filepath.write_text(request.content)
    else:
        # Default: YAML mock tool
        try:
            yaml.safe_load(request.content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e
        filepath = ctx.tools_dir / f"{request.name}.yml"
        filepath.write_text(request.content)

    return SaveToolResponse(
        name=request.name,
        path=str(filepath),
        message=f"Tool saved to {filepath}",
    )


# =============================================================================
# Dataset Management API
# =============================================================================


class DatasetInfo(BaseModel):
    """Information about a dataset."""

    id: str
    name: str
    description: str
    case_count: int
    path: str
    relative_path: str


class DatasetCaseInfo(BaseModel):
    """Information about a single test case."""

    id: str
    expected: list[str] = Field(default_factory=list)  # Can have multiple expected outcomes
    variables: dict[str, Any] = Field(default_factory=dict)
    tool_responses: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class DatasetDetail(BaseModel):
    """Detailed dataset information."""

    id: str
    name: str
    description: str
    scenario_id: str | None = None  # Linked scenario for goal discovery
    cases: list[DatasetCaseInfo]
    generator: dict[str, Any] | None = None
    path: str


class ScenarioGoalInfo(BaseModel):
    """Information about a goal from a scenario."""

    id: str
    name: str
    description: str
    outcome: bool = False


class SaveDatasetRequest(BaseModel):
    """Request to save a dataset."""

    id: str
    content: str  # YAML content


class SaveDatasetResponse(BaseModel):
    """Response from saving a dataset."""

    id: str
    path: str
    message: str


class RunDatasetRequest(BaseModel):
    """Request to run a scenario against a dataset."""

    scenario_id: str
    dataset_id: str
    model: str
    max_turns: int = 20
    max_tokens: int = 1024
    temperature: float = 0.7
    parallel: int = 1


class RunDatasetResponse(BaseModel):
    """Response from running a dataset."""

    scenario_id: str
    model: str
    dataset_id: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    avg_score: float
    avg_percentage: float
    by_expected: dict[str, dict[str, int]]
    total_time_ms: int
    case_results: list[dict[str, Any]]


@router.get("/local/datasets", response_model=list[DatasetInfo])
async def list_local_datasets() -> list[DatasetInfo]:
    """List datasets from local datasets/ directory."""
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    datasets = []
    datasets_dir = ctx.datasets_dir

    if datasets_dir.exists():
        for path in sorted(datasets_dir.glob("*.yml")):
            try:
                content = yaml.safe_load(path.read_text())
                if content:
                    case_count = 0
                    if "cases" in content:
                        case_count = len(content.get("cases", []))
                    elif "generator" in content:
                        # Estimate generated case count
                        gen = content.get("generator", {})
                        dims = gen.get("dimensions", {})
                        case_count = 1
                        for values in dims.values():
                            if isinstance(values, list):
                                case_count *= len(values)

                    datasets.append(
                        DatasetInfo(
                            id=path.stem,
                            name=content.get("name", path.stem),
                            description=content.get("description", ""),
                            case_count=case_count,
                            path=str(path),
                            relative_path=str(path.relative_to(ctx.root_dir)),
                        )
                    )
            except Exception as e:
                logger.warning(f"Error loading dataset {path}: {e}")
                continue

    return datasets


@router.get("/local/datasets/{dataset_id}", response_model=DatasetDetail)
async def get_local_dataset(dataset_id: str) -> DatasetDetail:
    """Get a specific dataset by ID.

    Args:
        dataset_id: The dataset identifier.

    Returns:
        Dataset details including all cases.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    datasets_dir = ctx.datasets_dir
    filepath = datasets_dir / f"{dataset_id}.yml"

    if not filepath.exists():
        filepath = datasets_dir / f"{dataset_id}.yaml"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    try:
        content = yaml.safe_load(filepath.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dataset: {e}") from e

    cases = []
    for case_data in content.get("cases", []):
        # Handle expected as string or list
        expected_raw = case_data.get("expected")
        if expected_raw is None:
            expected = []
        elif isinstance(expected_raw, list):
            expected = expected_raw
        else:
            expected = [expected_raw]

        cases.append(
            DatasetCaseInfo(
                id=case_data.get("id", ""),
                expected=expected,
                variables=case_data.get("variables", {}),
                tool_responses=case_data.get("tool_responses", {}),
                tags=case_data.get("tags", []),
            )
        )

    return DatasetDetail(
        id=dataset_id,
        name=content.get("name", dataset_id),
        description=content.get("description", ""),
        scenario_id=content.get("scenario_id"),
        cases=cases,
        generator=content.get("generator"),
        path=str(filepath),
    )


@router.get("/local/scenarios/{scenario_id}/goals", response_model=list[ScenarioGoalInfo])
async def get_scenario_goals(scenario_id: str) -> list[ScenarioGoalInfo]:
    """Get goals from a scenario for dataset editor dropdown.

    Args:
        scenario_id: The scenario identifier.

    Returns:
        List of goals with their outcome flag.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find the scenario file
    discovered = ctx.discover()
    scenario_path = None

    for s in discovered["scenarios"]:
        if s["id"] == scenario_id:
            scenario_path = Path(s["path"])
            break

    if not scenario_path:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")

    try:
        from sandboxy.scenarios.unified import load_unified_scenario

        spec = load_unified_scenario(scenario_path)

        goals = []
        if spec.evaluation and spec.evaluation.goals:
            for goal in spec.evaluation.goals:
                goals.append(
                    ScenarioGoalInfo(
                        id=goal.id,
                        name=goal.name,
                        description=goal.description,
                        outcome=goal.outcome,
                    )
                )

        return goals

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading scenario: {e}") from e


class ScenarioToolAction(BaseModel):
    """Information about a tool action."""

    name: str
    description: str = ""


class ScenarioToolInfo(BaseModel):
    """Information about a tool in a scenario."""

    name: str
    description: str = ""
    actions: list[ScenarioToolAction] = []


@router.get("/local/scenarios/{scenario_id}/tools", response_model=list[ScenarioToolInfo])
async def get_scenario_tools(scenario_id: str) -> list[ScenarioToolInfo]:
    """Get tools from a scenario for dataset editor dropdown.

    Args:
        scenario_id: The scenario identifier.

    Returns:
        List of tools with their actions.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find the scenario file
    discovered = ctx.discover()
    scenario_path = None

    for s in discovered["scenarios"]:
        if s["id"] == scenario_id:
            scenario_path = Path(s["path"])
            break

    if not scenario_path:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")

    try:
        from sandboxy.scenarios.unified import load_unified_scenario
        from sandboxy.tools.yaml_tools import YamlToolLoader

        spec = load_unified_scenario(scenario_path)
        loader = YamlToolLoader([ctx.tools_dir])

        tools_info: list[ScenarioToolInfo] = []

        # Get inline tools
        if spec.tools:
            inline_specs = loader.parse_inline_tools(spec.tools)
            for tool_name, tool_spec in inline_specs.items():
                actions = [
                    ScenarioToolAction(
                        name=action_name,
                        description=action_spec.description,
                    )
                    for action_name, action_spec in tool_spec.get_effective_actions().items()
                ]
                tools_info.append(
                    ScenarioToolInfo(
                        name=tool_name,
                        description=tool_spec.description,
                        actions=actions,
                    )
                )

        # Get tools from libraries
        for lib_name in spec.tools_from:
            lib_path = ctx.tools_dir / f"{lib_name}.yml"
            if not lib_path.exists():
                lib_path = ctx.tools_dir / f"{lib_name}.yaml"
            if lib_path.exists():
                library = loader.load_library_file(lib_path)
                for tool_name, tool_spec in library.tools.items():
                    actions = [
                        ScenarioToolAction(
                            name=action_name,
                            description=action_spec.description,
                        )
                        for action_name, action_spec in tool_spec.get_effective_actions().items()
                    ]
                    tools_info.append(
                        ScenarioToolInfo(
                            name=tool_name,
                            description=tool_spec.description,
                            actions=actions,
                        )
                    )

        return tools_info

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading scenario tools: {e}") from e


@router.post("/local/datasets", response_model=SaveDatasetResponse)
async def save_dataset(request: SaveDatasetRequest) -> SaveDatasetResponse:
    """Save a new dataset to the datasets/ directory.

    Args:
        request: Dataset ID and YAML content.

    Returns:
        Saved dataset info.
    """
    import re

    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Validate ID
    if not request.id:
        raise HTTPException(status_code=400, detail="Dataset ID is required")

    if not re.match(r"^[a-z0-9_-]+$", request.id):
        raise HTTPException(
            status_code=400,
            detail="Dataset ID must contain only lowercase letters, numbers, hyphens, and underscores",
        )

    # Validate YAML
    try:
        yaml.safe_load(request.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e

    # Ensure datasets directory exists
    datasets_dir = ctx.datasets_dir
    datasets_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    filepath = datasets_dir / f"{request.id}.yml"
    filepath.write_text(request.content)

    return SaveDatasetResponse(
        id=request.id,
        path=str(filepath),
        message=f"Dataset saved to {filepath}",
    )


@router.put("/local/datasets/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    request: SaveDatasetRequest,
) -> SaveDatasetResponse:
    """Update an existing dataset.

    Args:
        dataset_id: The dataset ID to update.
        request: New YAML content.

    Returns:
        Updated dataset info.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    datasets_dir = ctx.datasets_dir
    filepath = datasets_dir / f"{dataset_id}.yml"
    if not filepath.exists():
        filepath = datasets_dir / f"{dataset_id}.yaml"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    # Validate YAML
    try:
        yaml.safe_load(request.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}") from e

    # Update file
    filepath.write_text(request.content)

    return SaveDatasetResponse(
        id=dataset_id,
        path=str(filepath),
        message=f"Dataset updated at {filepath}",
    )


@router.delete("/local/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str) -> dict[str, str]:
    """Delete a dataset.

    Args:
        dataset_id: The dataset ID to delete.

    Returns:
        Confirmation message.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    datasets_dir = ctx.datasets_dir
    filepath = datasets_dir / f"{dataset_id}.yml"
    if not filepath.exists():
        filepath = datasets_dir / f"{dataset_id}.yaml"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    filepath.unlink()

    return {"message": f"Dataset {dataset_id} deleted"}


@router.post("/local/run-dataset", response_model=RunDatasetResponse)
async def run_with_dataset(request: RunDatasetRequest) -> RunDatasetResponse:
    """Run a scenario against a dataset.

    Args:
        request: Run configuration including scenario_id, dataset_id, and model.

    Returns:
        Dataset benchmark results.
    """
    ctx = get_local_context()
    if not ctx:
        raise HTTPException(status_code=500, detail="Not in local mode")

    # Find the scenario file
    discovered = ctx.discover()
    scenario_path = None

    for s in discovered["scenarios"]:
        if s["id"] == request.scenario_id:
            scenario_path = Path(s["path"])
            break

    if not scenario_path:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario not found: {request.scenario_id}",
        )

    # Find the dataset file
    datasets_dir = ctx.datasets_dir
    dataset_path = datasets_dir / f"{request.dataset_id}.yml"
    if not dataset_path.exists():
        dataset_path = datasets_dir / f"{request.dataset_id}.yaml"
        if not dataset_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Dataset not found: {request.dataset_id}",
            )

    try:
        from sandboxy.datasets import load_dataset, run_dataset, run_dataset_parallel
        from sandboxy.scenarios.unified import load_unified_scenario

        spec = load_unified_scenario(scenario_path)
        dataset = load_dataset(dataset_path)

        if request.parallel > 1:
            result = await run_dataset_parallel(
                scenario=spec,
                model=request.model,
                dataset=dataset,
                max_turns=request.max_turns,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                max_concurrent=request.parallel,
            )
        else:
            result = await run_dataset(
                scenario=spec,
                model=request.model,
                dataset=dataset,
                max_turns=request.max_turns,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

        # Save result
        from sandboxy.local.results import save_run_result

        save_run_result(
            f"{request.scenario_id}_dataset_{request.dataset_id}",
            result.to_dict(),
        )

        return RunDatasetResponse(
            scenario_id=result.scenario_id,
            model=result.model,
            dataset_id=result.dataset_id,
            total_cases=result.total_cases,
            passed_cases=result.passed_cases,
            failed_cases=result.failed_cases,
            pass_rate=result.pass_rate,
            avg_score=result.avg_score,
            avg_percentage=result.avg_percentage,
            by_expected=result.by_expected,
            total_time_ms=result.total_time_ms,
            case_results=[c.to_dict() for c in result.case_results],
        )

    except Exception as e:
        logger.exception(f"Error running dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
