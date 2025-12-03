"""FastAPI application factory and server runner."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sandboxy.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sandboxy",
        description="Interactive agent simulation and benchmarking platform",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from sandboxy.api.routes import agents, modules, sessions

    app.include_router(modules.router, prefix="/api/v1", tags=["modules"])
    app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])

    # Register WebSocket handler
    from sandboxy.api.websocket import router as ws_router

    app.include_router(ws_router)

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "0.2.0"}

    # Serve frontend static files in production
    frontend_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

    return app


# Create the app instance
app = create_app()


def run_server():
    """Run the server using uvicorn (entry point for sandboxy-server command)."""
    import uvicorn

    host = os.environ.get("SANDBOXY_HOST", "127.0.0.1")
    port = int(os.environ.get("SANDBOXY_PORT", "8000"))
    reload = os.environ.get("SANDBOXY_RELOAD", "").lower() == "true"

    print(f"Starting Sandboxy server at http://{host}:{port}")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "sandboxy.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
