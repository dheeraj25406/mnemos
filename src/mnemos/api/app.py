from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mnemos.api.v1 import (
    consolidation,
    entities,
    graph,
    health,
    memories,
    metrics,
    temporal,
)
from mnemos.core.config import get_settings
from mnemos.core.errors import MnemosError
from mnemos.core.logging import logger, setup_logging
from mnemos.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(level=settings.log_level)
    logger.info("Initializing Mnemos Temporal Memory Infrastructure...")
    try:
        await init_db()
        logger.info("Database schemas and pgvector extensions verified.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
    yield
    logger.info("Mnemos shutting down cleanly.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mnemos API",
        description="Temporal Memory Infrastructure for AI Agents — Persistent knowledge, temporal reasoning, evolving memory.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include v1 routers
    prefix = settings.api_v1_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(memories.router, prefix=prefix)
    app.include_router(entities.router, prefix=prefix)
    app.include_router(graph.router, prefix=prefix)
    app.include_router(temporal.router, prefix=prefix)
    app.include_router(consolidation.router, prefix=prefix)
    app.include_router(metrics.router, prefix=prefix)

    # Root redirect / ping
    @app.get("/")
    async def root():
        return {
            "product": "Mnemos",
            "tagline": "Persistent knowledge. Temporal reasoning. Evolving memory.",
            "documentation": "/docs",
            "health": f"{prefix}/health",
        }

    # Exception Handlers
    @app.exception_handler(MnemosError)
    async def mnemos_error_handler(request: Request, exc: MnemosError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.message, "details": exc.details},
        )

    return app


app = create_app()


def run_server():
    uvicorn.run(
        "mnemos.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run_server()
