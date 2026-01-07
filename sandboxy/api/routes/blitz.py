"""Blitz API routes - Quick AI showdowns with short, punchy responses."""

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sandboxy.blitz.templates import (
    BLITZ_TEMPLATES,
    RESPONSE_STYLES,
    get_template,
    list_all_templates,
)
from sandboxy.db.database import get_db
from sandboxy.db import models
from sandboxy.providers import get_registry

router = APIRouter(prefix="/blitz", tags=["blitz"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateBlitzRequest(BaseModel):
    """Request to create a new blitz."""

    prompt: str = Field(..., min_length=1, max_length=2000, description="The prompt to send to models")
    models: list[str] = Field(..., min_items=2, max_items=6, description="Model IDs to query")
    style: str = Field("brief", description="Response style")
    template_id: str | None = Field(None, description="Optional template ID for tracking")


class BlitzResponse(BaseModel):
    """A single model's response in a blitz."""

    content: str
    latency_ms: int
    tokens: int


class CreateBlitzResponse(BaseModel):
    """Response from creating a blitz."""

    id: str
    prompt: str
    style: str
    models: list[str]
    responses: dict[str, BlitzResponse]


class BlitzDetail(BaseModel):
    """Detailed blitz information."""

    id: str
    prompt: str
    prompt_template_id: str | None
    style: str
    models: list[str]
    responses: dict[str, Any]
    view_count: int
    video_url: str | None
    thumbnail_url: str | None
    created_at: str


class TemplateCategory(BaseModel):
    """A category of prompt templates."""

    id: str
    name: str
    icon: str
    templates: list[dict[str, Any]]


# =============================================================================
# Routes
# =============================================================================


@router.get("/styles")
async def list_styles() -> dict[str, str]:
    """List available response styles."""
    return RESPONSE_STYLES


@router.get("/templates/categories", response_model=list[TemplateCategory])
async def list_template_categories() -> list[TemplateCategory]:
    """List all prompt template categories."""
    return [
        TemplateCategory(
            id=cat_id,
            name=cat["name"],
            icon=cat["icon"],
            templates=cat["templates"],
        )
        for cat_id, cat in BLITZ_TEMPLATES.items()
    ]


@router.get("/templates/all")
async def list_templates() -> list[dict[str, Any]]:
    """List all templates flat."""
    return list_all_templates()


@router.get("/templates/{category}/{template_id}")
async def get_template_detail(
    category: str,
    template_id: str,
) -> dict[str, Any]:
    """Get a specific template."""
    template = get_template(category, template_id)
    if not template:
        raise HTTPException(404, "Template not found")

    cat = BLITZ_TEMPLATES.get(category, {})
    return {
        "category": category,
        "category_name": cat.get("name", ""),
        "category_icon": cat.get("icon", ""),
        **template,
    }


@router.post("", response_model=CreateBlitzResponse)
async def create_blitz(
    request: CreateBlitzRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateBlitzResponse:
    """Create a blitz by querying multiple models in parallel.

    Each model receives the same prompt with a response style
    to keep responses short and punchy.
    """
    # Validate style
    if request.style not in RESPONSE_STYLES:
        raise HTTPException(
            400,
            f"Invalid style: {request.style}. Valid: {list(RESPONSE_STYLES.keys())}",
        )

    # Validate models
    registry = get_registry()
    for model_id in request.models:
        try:
            registry.get_provider_for_model(model_id)
        except ValueError:
            raise HTTPException(400, f"Unknown model: {model_id}")

    # Build system prompt with style
    style_text = RESPONSE_STYLES[request.style]
    system_prompt = f"""You are participating in a fun AI showdown.

IMPORTANT: {style_text}

Be genuine, show personality, and don't hold back. This is for entertainment!"""

    # Query all models in parallel
    async def query_model(model_id: str) -> tuple[str, dict]:
        provider = registry.get_provider_for_model(model_id)
        start = time.time()

        try:
            response = await provider.complete(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                temperature=0.9,
                max_tokens=200,  # Keep it short
            )

            return model_id, {
                "content": response.content,
                "latency_ms": int((time.time() - start) * 1000),
                "tokens": response.output_tokens,
                "error": None,
            }
        except Exception as e:
            return model_id, {
                "content": "",
                "latency_ms": int((time.time() - start) * 1000),
                "tokens": 0,
                "error": str(e),
            }

    results = await asyncio.gather(*[query_model(m) for m in request.models])
    responses = dict(results)

    # Check if any succeeded
    successful = [m for m, r in responses.items() if not r.get("error")]
    if len(successful) < 2:
        errors = {m: r.get("error") for m, r in responses.items() if r.get("error")}
        raise HTTPException(500, f"Too many models failed: {errors}")

    # Save to database (still uses Clip model internally)
    blitz = models.Clip(
        prompt=request.prompt,
        prompt_template_id=request.template_id,
        constraint_type=request.style,
        models=request.models,
        responses=responses,
    )
    db.add(blitz)
    await db.commit()
    await db.refresh(blitz)

    return CreateBlitzResponse(
        id=blitz.id,
        prompt=blitz.prompt,
        style=blitz.constraint_type,
        models=blitz.models,
        responses={
            m: BlitzResponse(
                content=r["content"],
                latency_ms=r["latency_ms"],
                tokens=r["tokens"],
            )
            for m, r in responses.items()
            if not r.get("error")
        },
    )


@router.get("/{blitz_id}", response_model=BlitzDetail)
async def get_blitz(
    blitz_id: str,
    db: AsyncSession = Depends(get_db),
) -> BlitzDetail:
    """Get details of a specific blitz."""
    stmt = select(models.Clip).where(models.Clip.id == blitz_id)
    result = await db.execute(stmt)
    blitz = result.scalar_one_or_none()

    if not blitz:
        raise HTTPException(404, "Blitz not found")

    # Increment view count
    blitz.view_count += 1
    await db.commit()

    return BlitzDetail(
        id=blitz.id,
        prompt=blitz.prompt,
        prompt_template_id=blitz.prompt_template_id,
        style=blitz.constraint_type,
        models=blitz.models,
        responses=blitz.responses,
        view_count=blitz.view_count,
        video_url=blitz.video_url,
        thumbnail_url=blitz.thumbnail_url,
        created_at=blitz.created_at.isoformat(),
    )


@router.get("", response_model=list[BlitzDetail])
async def list_blitzes(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[BlitzDetail]:
    """List recent blitzes."""
    stmt = (
        select(models.Clip)
        .order_by(models.Clip.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    blitzes = result.scalars().all()

    return [
        BlitzDetail(
            id=b.id,
            prompt=b.prompt,
            prompt_template_id=b.prompt_template_id,
            style=b.constraint_type,
            models=b.models,
            responses=b.responses,
            view_count=b.view_count,
            video_url=b.video_url,
            thumbnail_url=b.thumbnail_url,
            created_at=b.created_at.isoformat(),
        )
        for b in blitzes
    ]


