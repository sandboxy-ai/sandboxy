"""Module CRUD routes."""

from pathlib import Path
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sandboxy.db import crud
from sandboxy.db.database import get_db

router = APIRouter()

# Path to YAML modules directory (for loading file-based modules)
MODULES_DIR = Path(__file__).parent.parent.parent.parent / "modules"


class ModuleResponse(BaseModel):
    """Response model for a module."""

    id: str
    slug: str
    name: str
    description: str | None
    icon: str | None
    category: str | None
    yaml_content: str | None = None  # Only included in detail view

    class Config:
        from_attributes = True


class ModuleListResponse(BaseModel):
    """Response model for module listing."""

    modules: list[ModuleResponse]
    count: int


class ModuleCreate(BaseModel):
    """Request model for creating a module."""

    slug: str
    name: str
    description: str | None = None
    icon: str | None = None
    category: str | None = None
    yaml_content: str


class ModuleUpdate(BaseModel):
    """Request model for updating a module."""

    name: str | None = None
    description: str | None = None
    icon: str | None = None
    category: str | None = None
    yaml_content: str | None = None


def _load_yaml_modules() -> list[ModuleResponse]:
    """Load modules from YAML files in the modules directory."""
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for path in MODULES_DIR.glob("*.y*ml"):
        try:
            content = path.read_text()
            data = yaml.safe_load(content)
            if data and isinstance(data, dict):
                modules.append(
                    ModuleResponse(
                        id=f"file:{path.stem}",
                        slug=path.stem,
                        name=data.get("name", data.get("id", path.stem)),
                        description=data.get("description"),
                        icon=data.get("icon"),
                        category=data.get("category"),
                        yaml_content=None,  # Don't include full content in list
                    )
                )
        except Exception:
            # Skip invalid files
            continue

    return modules


@router.get("/modules", response_model=ModuleListResponse)
async def list_modules(
    db: Annotated[AsyncSession, Depends(get_db)],
    include_files: bool = True,
):
    """List all available modules.

    Args:
        include_files: Whether to include file-based modules from modules/ directory
    """
    # Get database modules
    db_modules = await crud.get_modules(db)
    modules = [
        ModuleResponse(
            id=m.id,
            slug=m.slug,
            name=m.name,
            description=m.description,
            icon=m.icon,
            category=m.category,
        )
        for m in db_modules
    ]

    # Add file-based modules
    if include_files:
        file_modules = _load_yaml_modules()
        # Don't duplicate if slug already exists in DB
        db_slugs = {m.slug for m in modules}
        for fm in file_modules:
            if fm.slug not in db_slugs:
                modules.append(fm)

    return ModuleListResponse(modules=modules, count=len(modules))


@router.get("/modules/{slug}", response_model=ModuleResponse)
async def get_module(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a module by slug."""
    # Try database first
    module = await crud.get_module_by_slug(db, slug)
    if module:
        return ModuleResponse(
            id=module.id,
            slug=module.slug,
            name=module.name,
            description=module.description,
            icon=module.icon,
            category=module.category,
            yaml_content=module.yaml_content,
        )

    # Try file-based module
    for ext in [".yml", ".yaml"]:
        path = MODULES_DIR / f"{slug}{ext}"
        if path.exists():
            content = path.read_text()
            data = yaml.safe_load(content)
            return ModuleResponse(
                id=f"file:{slug}",
                slug=slug,
                name=data.get("name", data.get("id", slug)),
                description=data.get("description"),
                icon=data.get("icon"),
                category=data.get("category"),
                yaml_content=content,
            )

    raise HTTPException(status_code=404, detail="Module not found")


@router.post("/modules", response_model=ModuleResponse, status_code=201)
async def create_module(
    module: ModuleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new module."""
    # Check if slug already exists
    existing = await crud.get_module_by_slug(db, module.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Module with this slug already exists")

    # Validate YAML
    try:
        yaml.safe_load(module.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    created = await crud.create_module(
        db,
        slug=module.slug,
        name=module.name,
        yaml_content=module.yaml_content,
        description=module.description,
        icon=module.icon,
        category=module.category,
    )

    return ModuleResponse(
        id=created.id,
        slug=created.slug,
        name=created.name,
        description=created.description,
        icon=created.icon,
        category=created.category,
        yaml_content=created.yaml_content,
    )


@router.put("/modules/{slug}", response_model=ModuleResponse)
async def update_module(
    slug: str,
    update: ModuleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing module."""
    module = await crud.get_module_by_slug(db, slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Validate YAML if provided
    if update.yaml_content:
        try:
            yaml.safe_load(update.yaml_content)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    updated = await crud.update_module(
        db,
        module,
        name=update.name,
        yaml_content=update.yaml_content,
        description=update.description,
        icon=update.icon,
        category=update.category,
    )

    return ModuleResponse(
        id=updated.id,
        slug=updated.slug,
        name=updated.name,
        description=updated.description,
        icon=updated.icon,
        category=updated.category,
        yaml_content=updated.yaml_content,
    )


@router.delete("/modules/{slug}", status_code=204)
async def delete_module(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a module."""
    module = await crud.get_module_by_slug(db, slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    await crud.delete_module(db, module)
