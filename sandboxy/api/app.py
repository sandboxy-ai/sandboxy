"""FastAPI application factory for local development."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

from sandboxy.logging import setup_logging

load_dotenv()
setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _local_lifespan(app: FastAPI):
    """Lifespan handler for local mode (no database)."""
    yield


def create_local_app(
    root_dir: Path,
    local_ui_path: Path | None = None,
) -> FastAPI:
    """Create FastAPI app for local development mode.

    This version is lightweight and reads from the local filesystem.

    Args:
        root_dir: Working directory for scenarios/tools/agents.
        local_ui_path: Path to local UI static files.
    """
    from sandboxy.local.context import LocalContext, set_local_context

    ctx = LocalContext(root_dir=root_dir)
    set_local_context(ctx)

    app = FastAPI(
        title="Sandboxy Local",
        description="Local development server for Sandboxy",
        version="0.2.0",
        lifespan=_local_lifespan,
    )

    # CORS - allow all origins in local mode
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Local routes only
    from sandboxy.api.routes import agents, tools
    from sandboxy.api.routes import local as local_routes

    app.include_router(local_routes.router, prefix="/api/v1", tags=["local"])
    app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    app.include_router(tools.router, prefix="/api/v1", tags=["tools"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "mode": "local"}

    # Serve local UI if available
    if local_ui_path and local_ui_path.exists():
        app.mount("/", StaticFiles(directory=str(local_ui_path), html=True), name="local-ui")

    return app
