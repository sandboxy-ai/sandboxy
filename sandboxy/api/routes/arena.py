"""Arena API routes for multi-model comparison."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sandboxy.arena import ArenaPrompt, ArenaRunner
from sandboxy.arena.prompts import (
    JudgeConfig,
    JudgeTemplate,
    JudgeType,
    PromptCategory,
    get_builtin_prompt,
    get_judge_template,
    list_builtin_prompts,
    list_judge_templates,
)
from sandboxy.db.database import get_db
from sandboxy.db import models
from sandboxy.providers import get_registry

router = APIRouter(prefix="/arena", tags=["arena"])


# =============================================================================
# Request/Response Models
# =============================================================================


class RunRequest(BaseModel):
    """Request to run a prompt against models."""

    prompt_id: str | None = Field(None, description="ID of existing prompt to use")
    prompt_text: str | None = Field(None, description="Custom prompt text (if no prompt_id)")
    system_prompt: str | None = Field(None, description="System prompt")
    models: list[str] = Field(..., description="List of model IDs to test")
    variables: dict[str, Any] | None = Field(None, description="Variable values")
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int = Field(1024, ge=1, le=8192)
    # Judge configuration for custom prompts
    judge_template_id: str | None = Field(None, description="ID of judge template to use")
    judge_config: dict[str, Any] | None = Field(None, description="Inline judge configuration")


class RunResponse(BaseModel):
    """Response from an arena run."""

    id: str
    prompt_text: str
    models: list[str]
    results: dict[str, dict[str, Any]]
    judgments: dict[str, dict[str, Any]]
    winner: str | None
    ranking: list[tuple[str, float]]
    total_latency_ms: int
    total_cost_usd: float | None


class PromptRequest(BaseModel):
    """Request to create a prompt (challenge)."""

    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1)
    category: str = Field("custom")
    system_prompt: str | None = None
    judge_type: str = Field("llm")
    judge_config: dict[str, Any] = Field(default_factory=dict)
    judge_template_id: str | None = None  # Reference to a reusable judge template
    variables: list[dict[str, Any]] | None = None
    tags: list[str] | None = None


class PromptResponse(BaseModel):
    """Response with prompt (challenge) details."""

    id: str
    slug: str
    title: str
    text: str
    category: str
    system_prompt: str | None
    judge_config: dict[str, Any]
    judge_template_id: str | None = None
    variables: list[dict[str, Any]] | None
    tags: list[str] | None
    is_featured: bool
    run_count: int = 0


class ModelsResponse(BaseModel):
    """Response with available models."""

    models: list[dict[str, Any]]
    providers: list[str]


class JudgeTemplateRequest(BaseModel):
    """Request to create a judge template."""

    slug: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    judge_type: str = Field("llm")
    model: str | None = None
    rubric: str | None = None
    pattern: str | None = None
    case_sensitive: bool = False
    min_length: int | None = None
    max_length: int | None = None
    voters: list[str] | None = None
    pass_threshold: float = 0.5


class JudgeTemplateResponse(BaseModel):
    """Response with judge template details."""

    id: str
    slug: str
    name: str
    description: str | None
    judge_type: str
    model: str | None
    rubric: str | None
    pattern: str | None
    case_sensitive: bool
    min_length: int | None
    max_length: int | None
    voters: list[str] | None
    pass_threshold: float
    is_builtin: bool = False


# =============================================================================
# Routes
# =============================================================================


@router.post("/run", response_model=RunResponse)
async def run_arena(
    request: RunRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Run a prompt against multiple models.

    Either provide a prompt_id for an existing prompt, or provide
    prompt_text for a custom prompt.
    """
    # Get or build prompt
    if request.prompt_id:
        # Try built-in first
        prompt = get_builtin_prompt(request.prompt_id)
        if not prompt:
            # Try database
            from sqlalchemy import select
            stmt = select(models.ArenaPrompt).where(
                (models.ArenaPrompt.id == request.prompt_id) |
                (models.ArenaPrompt.slug == request.prompt_id)
            )
            result = await db.execute(stmt)
            db_prompt = result.scalar_one_or_none()

            if not db_prompt:
                raise HTTPException(404, f"Prompt not found: {request.prompt_id}")

            prompt = ArenaPrompt(
                id=db_prompt.id,
                title=db_prompt.title,
                text=db_prompt.text,
                category=PromptCategory(db_prompt.category),
                system_prompt=db_prompt.system_prompt,
                judge=JudgeConfig.from_dict(db_prompt.judge_config),
                tags=db_prompt.tags or [],
            )
    elif request.prompt_text:
        # Custom prompt - determine judge config
        judge_config: JudgeConfig

        if request.judge_template_id:
            # Use referenced judge template
            judge_template = get_judge_template(request.judge_template_id)
            if judge_template:
                judge_config = judge_template.to_judge_config()
            else:
                raise HTTPException(400, f"Judge template not found: {request.judge_template_id}")
        elif request.judge_config:
            # Use inline judge config
            judge_config = JudgeConfig.from_dict(request.judge_config)
        else:
            # Default LLM judge
            judge_config = JudgeConfig(type=JudgeType.LLM)

        prompt = ArenaPrompt(
            text=request.prompt_text,
            system_prompt=request.system_prompt,
            judge=judge_config,
        )
    else:
        raise HTTPException(400, "Either prompt_id or prompt_text required")

    # Validate models
    if not request.models:
        raise HTTPException(400, "At least one model required")
    if len(request.models) > 10:
        raise HTTPException(400, "Maximum 10 models per run")

    # Run arena
    runner = ArenaRunner()
    try:
        run = await runner.run(
            prompt=prompt,
            models=request.models,
            variables=request.variables,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(500, f"Arena run failed: {e}")

    # Get client IP
    forwarded = req.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        req.client.host if req.client else None
    )

    # Save to database
    db_run = models.ArenaRun(
        id=run.id,
        prompt_id=prompt.id if hasattr(prompt, 'id') and prompt.id else None,
        prompt_text=run.prompt_text,
        system_prompt=run.system_prompt,
        variables=run.variables,
        models=run.models,
        total_latency_ms=run.total_latency_ms,
        total_cost_usd=run.total_cost_usd,
        ip_address=ip,
    )
    db.add(db_run)

    # Save results
    for model_id, result in run.results.items():
        judgment = run.judgments.get(model_id)
        db_result = models.ArenaResult(
            run_id=run.id,
            model_id=model_id,
            response=result.response,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            error=result.error,
            score=judgment.score if judgment else None,
            passed=judgment.passed if judgment else None,
            judgment_reasoning=judgment.reasoning if judgment else None,
            judge_type=judgment.judge_type if judgment else None,
        )
        db.add(db_result)

    await db.commit()

    return RunResponse(
        id=run.id,
        prompt_text=run.prompt_text,
        models=run.models,
        results={k: v.to_dict() for k, v in run.results.items()},
        judgments={k: v.to_dict() for k, v in run.judgments.items()},
        winner=run.get_winner(),
        ranking=run.get_ranking(),
        total_latency_ms=run.total_latency_ms,
        total_cost_usd=run.total_cost_usd,
    )


@router.get("/run/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get details of a specific arena run."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(models.ArenaRun).where(
        models.ArenaRun.id == run_id
    ).options(
        selectinload(models.ArenaRun.results),
        selectinload(models.ArenaRun.video),
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(404, "Run not found")

    return {
        "id": run.id,
        "prompt_id": run.prompt_id,
        "prompt_text": run.prompt_text,
        "system_prompt": run.system_prompt,
        "models": run.models,
        "variables": run.variables,
        "total_latency_ms": run.total_latency_ms,
        "total_cost_usd": run.total_cost_usd,
        "created_at": run.created_at.isoformat(),
        "results": [
            {
                "model_id": r.model_id,
                "response": r.response,
                "latency_ms": r.latency_ms,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.cost_usd,
                "error": r.error,
                "score": r.score,
                "passed": r.passed,
                "judgment_reasoning": r.judgment_reasoning,
                "judge_type": r.judge_type,
            }
            for r in run.results
        ],
        "video": {
            "status": run.video.status,
            "cdn_url": run.video.cdn_url,
            "thumbnail_url": run.video.thumbnail_url,
        } if run.video else None,
    }


@router.get("/prompts")
async def list_prompts(
    category: str | None = None,
    featured: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PromptResponse]:
    """List available prompts (challenges)."""
    # Start with built-in prompts
    prompts = []
    for p in list_builtin_prompts():
        if category and p.category.value != category:
            continue
        prompts.append(PromptResponse(
            id=p.id or "",
            slug=p.id or "",
            title=p.title or "",
            text=p.text,
            category=p.category.value,
            system_prompt=p.system_prompt,
            judge_config=p.judge.to_dict(),
            judge_template_id=p.judge_template_id,
            variables=[v.__dict__ for v in p.variables] if p.variables else None,
            tags=p.tags,
            is_featured=False,
        ))

    # Add database prompts
    from sqlalchemy import select
    stmt = select(models.ArenaPrompt).where(models.ArenaPrompt.is_public == True)
    if category:
        stmt = stmt.where(models.ArenaPrompt.category == category)
    if featured:
        stmt = stmt.where(models.ArenaPrompt.is_featured == True)

    result = await db.execute(stmt)
    for db_prompt in result.scalars():
        prompts.append(PromptResponse(
            id=db_prompt.id,
            slug=db_prompt.slug,
            title=db_prompt.title,
            text=db_prompt.text,
            category=db_prompt.category,
            system_prompt=db_prompt.system_prompt,
            judge_config=db_prompt.judge_config,
            judge_template_id=db_prompt.judge_template_id,
            variables=db_prompt.variables,
            tags=db_prompt.tags,
            is_featured=db_prompt.is_featured,
        ))

    return prompts


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Get a specific prompt (challenge)."""
    # Try built-in first
    prompt = get_builtin_prompt(prompt_id)
    if prompt:
        return PromptResponse(
            id=prompt.id or "",
            slug=prompt.id or "",
            title=prompt.title or "",
            text=prompt.text,
            category=prompt.category.value,
            system_prompt=prompt.system_prompt,
            judge_config=prompt.judge.to_dict(),
            judge_template_id=prompt.judge_template_id,
            variables=[v.__dict__ for v in prompt.variables] if prompt.variables else None,
            tags=prompt.tags,
            is_featured=False,
        )

    # Try database
    from sqlalchemy import select
    stmt = select(models.ArenaPrompt).where(
        (models.ArenaPrompt.id == prompt_id) |
        (models.ArenaPrompt.slug == prompt_id)
    )
    result = await db.execute(stmt)
    db_prompt = result.scalar_one_or_none()

    if not db_prompt:
        raise HTTPException(404, "Prompt not found")

    return PromptResponse(
        id=db_prompt.id,
        slug=db_prompt.slug,
        title=db_prompt.title,
        text=db_prompt.text,
        category=db_prompt.category,
        system_prompt=db_prompt.system_prompt,
        judge_config=db_prompt.judge_config,
        judge_template_id=db_prompt.judge_template_id,
        variables=db_prompt.variables,
        tags=db_prompt.tags,
        is_featured=db_prompt.is_featured,
    )


@router.post("/prompts")
async def create_prompt(
    request: PromptRequest,
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Create a new prompt (challenge)."""
    # Check slug doesn't exist
    from sqlalchemy import select
    stmt = select(models.ArenaPrompt).where(models.ArenaPrompt.slug == request.slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(400, f"Prompt with slug '{request.slug}' already exists")

    # Validate judge template if provided
    if request.judge_template_id and not get_judge_template(request.judge_template_id):
        # Check database for user-created templates
        stmt = select(models.JudgeTemplate).where(
            (models.JudgeTemplate.id == request.judge_template_id) |
            (models.JudgeTemplate.slug == request.judge_template_id)
        )
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(400, f"Judge template '{request.judge_template_id}' not found")

    # Build judge config
    judge_config = {
        "type": request.judge_type,
        **request.judge_config,
    }

    db_prompt = models.ArenaPrompt(
        slug=request.slug,
        title=request.title,
        text=request.text,
        category=request.category,
        system_prompt=request.system_prompt,
        judge_config=judge_config,
        judge_template_id=request.judge_template_id,
        variables=request.variables,
        tags=request.tags,
        is_public=True,
        is_featured=False,
    )
    db.add(db_prompt)
    await db.commit()
    await db.refresh(db_prompt)

    return PromptResponse(
        id=db_prompt.id,
        slug=db_prompt.slug,
        title=db_prompt.title,
        text=db_prompt.text,
        category=db_prompt.category,
        system_prompt=db_prompt.system_prompt,
        judge_config=db_prompt.judge_config,
        judge_template_id=db_prompt.judge_template_id,
        variables=db_prompt.variables,
        tags=db_prompt.tags,
        is_featured=db_prompt.is_featured,
    )


@router.get("/models")
async def list_models() -> ModelsResponse:
    """List available models."""
    registry = get_registry()
    models_list = []

    for model in registry.list_all_models():
        models_list.append({
            "id": model.id,
            "name": model.name,
            "provider": model.provider,
            "context_length": model.context_length,
            "input_cost_per_million": model.input_cost_per_million,
            "output_cost_per_million": model.output_cost_per_million,
            "supports_vision": model.supports_vision,
            "supports_streaming": model.supports_streaming,
        })

    return ModelsResponse(
        models=models_list,
        providers=registry.available_providers,
    )


@router.get("/categories")
async def list_categories() -> list[dict[str, str]]:
    """List prompt categories."""
    return [
        {"id": c.value, "name": c.value.replace("_", " ").title()}
        for c in PromptCategory
    ]


# =============================================================================
# Judge Template Routes
# =============================================================================


@router.get("/judges")
async def list_judges(
    db: AsyncSession = Depends(get_db),
) -> list[JudgeTemplateResponse]:
    """List available judge templates.

    Returns both built-in YAML judges and user-created database judges.
    """
    judges = []

    # Add built-in judges from YAML files
    for j in list_judge_templates():
        judges.append(JudgeTemplateResponse(
            id=j.id,
            slug=j.id,
            name=j.name,
            description=j.description,
            judge_type=j.type.value,
            model=j.model,
            rubric=j.rubric,
            pattern=j.pattern,
            case_sensitive=j.case_sensitive,
            min_length=j.min_length,
            max_length=j.max_length,
            voters=j.voters,
            pass_threshold=j.pass_threshold,
            is_builtin=True,
        ))

    # Add database judges
    from sqlalchemy import select
    stmt = select(models.JudgeTemplate).where(models.JudgeTemplate.is_public == True)
    result = await db.execute(stmt)
    for db_judge in result.scalars():
        judges.append(JudgeTemplateResponse(
            id=db_judge.id,
            slug=db_judge.slug,
            name=db_judge.name,
            description=db_judge.description,
            judge_type=db_judge.judge_type,
            model=db_judge.model,
            rubric=db_judge.rubric,
            pattern=db_judge.pattern,
            case_sensitive=db_judge.case_sensitive,
            min_length=db_judge.min_length,
            max_length=db_judge.max_length,
            voters=db_judge.voters,
            pass_threshold=db_judge.pass_threshold,
            is_builtin=db_judge.is_builtin,
        ))

    return judges


@router.get("/judges/{judge_id}")
async def get_judge(
    judge_id: str,
    db: AsyncSession = Depends(get_db),
) -> JudgeTemplateResponse:
    """Get a specific judge template."""
    # Try built-in first
    judge = get_judge_template(judge_id)
    if judge:
        return JudgeTemplateResponse(
            id=judge.id,
            slug=judge.id,
            name=judge.name,
            description=judge.description,
            judge_type=judge.type.value,
            model=judge.model,
            rubric=judge.rubric,
            pattern=judge.pattern,
            case_sensitive=judge.case_sensitive,
            min_length=judge.min_length,
            max_length=judge.max_length,
            voters=judge.voters,
            pass_threshold=judge.pass_threshold,
            is_builtin=True,
        )

    # Try database
    from sqlalchemy import select
    stmt = select(models.JudgeTemplate).where(
        (models.JudgeTemplate.id == judge_id) |
        (models.JudgeTemplate.slug == judge_id)
    )
    result = await db.execute(stmt)
    db_judge = result.scalar_one_or_none()

    if not db_judge:
        raise HTTPException(404, "Judge template not found")

    return JudgeTemplateResponse(
        id=db_judge.id,
        slug=db_judge.slug,
        name=db_judge.name,
        description=db_judge.description,
        judge_type=db_judge.judge_type,
        model=db_judge.model,
        rubric=db_judge.rubric,
        pattern=db_judge.pattern,
        case_sensitive=db_judge.case_sensitive,
        min_length=db_judge.min_length,
        max_length=db_judge.max_length,
        voters=db_judge.voters,
        pass_threshold=db_judge.pass_threshold,
        is_builtin=db_judge.is_builtin,
    )


@router.post("/judges")
async def create_judge(
    request: JudgeTemplateRequest,
    db: AsyncSession = Depends(get_db),
) -> JudgeTemplateResponse:
    """Create a new judge template."""
    # Check slug doesn't exist
    from sqlalchemy import select
    stmt = select(models.JudgeTemplate).where(models.JudgeTemplate.slug == request.slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(400, f"Judge template with slug '{request.slug}' already exists")

    # Also check built-in judges
    if get_judge_template(request.slug):
        raise HTTPException(400, f"Judge template with slug '{request.slug}' already exists (built-in)")

    db_judge = models.JudgeTemplate(
        slug=request.slug,
        name=request.name,
        description=request.description,
        judge_type=request.judge_type,
        model=request.model,
        rubric=request.rubric,
        pattern=request.pattern,
        case_sensitive=request.case_sensitive,
        min_length=request.min_length,
        max_length=request.max_length,
        voters=request.voters,
        pass_threshold=request.pass_threshold,
        is_public=True,
        is_builtin=False,
    )
    db.add(db_judge)
    await db.commit()
    await db.refresh(db_judge)

    return JudgeTemplateResponse(
        id=db_judge.id,
        slug=db_judge.slug,
        name=db_judge.name,
        description=db_judge.description,
        judge_type=db_judge.judge_type,
        model=db_judge.model,
        rubric=db_judge.rubric,
        pattern=db_judge.pattern,
        case_sensitive=db_judge.case_sensitive,
        min_length=db_judge.min_length,
        max_length=db_judge.max_length,
        voters=db_judge.voters,
        pass_threshold=db_judge.pass_threshold,
        is_builtin=db_judge.is_builtin,
    )


@router.get("/judge-types")
async def list_judge_types() -> list[dict[str, str]]:
    """List available judge types."""
    return [
        {"id": "llm", "name": "LLM Judge", "description": "Use an AI model to evaluate responses"},
        {"id": "contains", "name": "Contains", "description": "Check if response contains specific text"},
        {"id": "regex", "name": "Regex", "description": "Match response against a regex pattern"},
        {"id": "exact", "name": "Exact Match", "description": "Check for exact match (after normalization)"},
        {"id": "length", "name": "Length", "description": "Check response length constraints"},
        {"id": "consensus", "name": "Consensus", "description": "Multiple models vote on quality"},
    ]
