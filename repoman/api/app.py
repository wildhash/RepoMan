"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repoman.api.routes import jobs, repos, ws
from repoman.config import Settings
from repoman.core.events import EventBus


def create_app(config: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Application settings. Defaults to Settings().

    Returns:
        Configured FastAPI application instance.
    """
    cfg = config or Settings()

    app = FastAPI(
        title="RepoMan API",
        description="Multi-model agentic repository transformation system",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach shared state
    app.state.config = cfg
    app.state.jobs: dict = {}
    app.state.event_bus = EventBus()

    # Register routers
    app.include_router(repos.router)
    app.include_router(jobs.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health() -> dict:
        """Health check endpoint.

        Returns:
            Status dict.
        """
        return {"status": "ok"}

    return app
