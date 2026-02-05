"""API routes for local provider management."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sandboxy.providers.config import (
    LocalProviderConfig,
    ProviderStatusEnum,
    load_providers_config,
    save_providers_config,
)
from sandboxy.providers.local import LocalProvider
from sandboxy.providers.registry import reload_local_providers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


# --- Response Models ---


class ProviderSummary(BaseModel):
    """Summary of a provider for list view."""

    name: str
    type: str
    base_url: str
    enabled: bool
    status: ProviderStatusEnum
    model_count: int
    models: list[str] = Field(default_factory=list)


class ProviderListResponse(BaseModel):
    """Response for GET /api/v1/providers."""

    providers: list[ProviderSummary]


class LocalModelInfoResponse(BaseModel):
    """Model info in API response."""

    id: str
    name: str
    context_length: int
    supports_tools: bool
    is_local: bool = True


class ProviderStatusResponse(BaseModel):
    """Provider connection status."""

    status: ProviderStatusEnum
    last_checked: str | None = None
    available_models: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    error_message: str | None = None


class ProviderDetailResponse(BaseModel):
    """Response for GET /api/v1/providers/{name}."""

    config: dict[str, Any]  # LocalProviderConfig as dict
    status: ProviderStatusResponse
    models: list[LocalModelInfoResponse]


class AddProviderRequest(BaseModel):
    """Request body for POST /api/v1/providers."""

    name: str
    type: Literal["ollama", "lmstudio", "vllm", "openai-compatible"] = "openai-compatible"
    base_url: str
    api_key: str | None = None
    models: list[str] = Field(default_factory=list)
    default_params: dict[str, Any] = Field(default_factory=dict)


class UpdateProviderRequest(BaseModel):
    """Request body for PATCH /api/v1/providers/{name}."""

    enabled: bool | None = None
    api_key: str | None = None
    models: list[str] | None = None
    default_params: dict[str, Any] | None = None


class TestConnectionResponse(BaseModel):
    """Response for POST /api/v1/providers/{name}/test."""

    success: bool
    latency_ms: int | None = None
    models_found: list[str] = Field(default_factory=list)
    error: str | None = None


class RefreshModelsResponse(BaseModel):
    """Response for POST /api/v1/providers/{name}/refresh."""

    models_found: list[str]
    models_added: list[str]
    models_removed: list[str]


class ErrorDetail(BaseModel):
    """Standard error response."""

    code: str
    message: str
    details: dict[str, Any] | None = None


# --- Routes ---


@router.get("", response_model=ProviderListResponse)
async def list_providers() -> ProviderListResponse:
    """List all configured providers with status."""
    config = load_providers_config()

    summaries: list[ProviderSummary] = []
    for pconfig in config.providers:
        provider = LocalProvider(pconfig)
        try:
            status = await provider.test_connection()
            summaries.append(
                ProviderSummary(
                    name=pconfig.name,
                    type=pconfig.type,
                    base_url=pconfig.base_url,
                    enabled=pconfig.enabled,
                    status=status.status,
                    model_count=len(status.available_models),
                    models=status.available_models,
                )
            )
        except Exception:
            summaries.append(
                ProviderSummary(
                    name=pconfig.name,
                    type=pconfig.type,
                    base_url=pconfig.base_url,
                    enabled=pconfig.enabled,
                    status=ProviderStatusEnum.ERROR,
                    model_count=0,
                    models=[],
                )
            )
        finally:
            await provider.close()

    return ProviderListResponse(providers=summaries)


@router.post("", response_model=ProviderSummary, status_code=status.HTTP_201_CREATED)
async def add_provider(request: AddProviderRequest) -> ProviderSummary:
    """Add a new provider."""
    config = load_providers_config()

    # Check for duplicate
    if config.get_provider(request.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(
                code="provider_exists",
                message=f"Provider '{request.name}' already exists",
            ).model_dump(),
        )

    # Validate and create config
    try:
        provider_config = LocalProviderConfig(
            name=request.name,
            type=request.type,
            base_url=request.base_url,
            api_key=request.api_key,
            models=request.models,
            default_params=request.default_params,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="validation_error",
                message=str(e),
            ).model_dump(),
        ) from e

    # Test connection
    provider = LocalProvider(provider_config)
    try:
        conn_status = await provider.test_connection()
    finally:
        await provider.close()

    # Save config
    config.add_provider(provider_config)
    save_providers_config(config)
    reload_local_providers()

    return ProviderSummary(
        name=provider_config.name,
        type=provider_config.type,
        base_url=provider_config.base_url,
        enabled=provider_config.enabled,
        status=conn_status.status,
        model_count=len(conn_status.available_models),
    )


@router.get("/{name}", response_model=ProviderDetailResponse)
async def get_provider(name: str) -> ProviderDetailResponse:
    """Get detailed provider info including models."""
    config = load_providers_config()
    provider_config = config.get_provider(name)

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="provider_not_found",
                message=f"Provider '{name}' not found",
                details={"available_providers": [p.name for p in config.providers]},
            ).model_dump(),
        )

    provider = LocalProvider(provider_config)
    try:
        conn_status = await provider.test_connection()
        models = await provider.refresh_models()
    finally:
        await provider.close()

    return ProviderDetailResponse(
        config=provider_config.model_dump(),
        status=ProviderStatusResponse(
            status=conn_status.status,
            last_checked=conn_status.last_checked.isoformat() if conn_status.last_checked else None,
            available_models=conn_status.available_models,
            latency_ms=conn_status.latency_ms,
            error_message=conn_status.error_message,
        ),
        models=[
            LocalModelInfoResponse(
                id=m.id,
                name=m.name,
                context_length=m.context_length,
                supports_tools=m.supports_tools,
            )
            for m in models
        ],
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(name: str) -> None:
    """Remove a provider."""
    config = load_providers_config()

    if not config.remove_provider(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="provider_not_found",
                message=f"Provider '{name}' not found",
            ).model_dump(),
        )

    save_providers_config(config)
    reload_local_providers()


@router.patch("/{name}", response_model=dict)
async def update_provider(name: str, request: UpdateProviderRequest) -> dict:
    """Update provider configuration."""
    config = load_providers_config()

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code="validation_error",
                message="No fields to update",
            ).model_dump(),
        )

    updated = config.update_provider(name, **updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="provider_not_found",
                message=f"Provider '{name}' not found",
            ).model_dump(),
        )

    save_providers_config(config)
    reload_local_providers()

    return updated.model_dump()


@router.post("/{name}/test", response_model=TestConnectionResponse)
async def test_provider_connection(name: str) -> TestConnectionResponse:
    """Test provider connection."""
    config = load_providers_config()
    provider_config = config.get_provider(name)

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="provider_not_found",
                message=f"Provider '{name}' not found",
            ).model_dump(),
        )

    provider = LocalProvider(provider_config)
    try:
        conn_status = await provider.test_connection()
    finally:
        await provider.close()

    return TestConnectionResponse(
        success=conn_status.status == ProviderStatusEnum.CONNECTED,
        latency_ms=conn_status.latency_ms,
        models_found=conn_status.available_models,
        error=conn_status.error_message,
    )


@router.post("/{name}/refresh", response_model=RefreshModelsResponse)
async def refresh_provider_models(name: str) -> RefreshModelsResponse:
    """Refresh model list from provider."""
    config = load_providers_config()
    provider_config = config.get_provider(name)

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="provider_not_found",
                message=f"Provider '{name}' not found",
            ).model_dump(),
        )

    # Get current models
    old_models = set(provider_config.models)

    provider = LocalProvider(provider_config)
    try:
        models = await provider.refresh_models()
    finally:
        await provider.close()

    new_models = {m.id for m in models}

    return RefreshModelsResponse(
        models_found=list(new_models),
        models_added=list(new_models - old_models),
        models_removed=list(old_models - new_models),
    )
