"""FastAPI application initialization."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database.client import init_db, close_db
from app.logging import setup_logging
from app.routes import health, solver

logger = logging.getLogger(__name__)
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.dev_mode:
        logger.warning(
            "DEV_MODE is enabled — API token auth is active. "
            "Disable in production."
        )
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def dev_token_middleware(request: Request, call_next):
    """
    When DEV_MODE=true, allow requests that carry the shared dev token as a
    Bearer token to bypass any future auth guards.

    Usage:
        curl -H "Authorization: Bearer schedula-dev-token-local" http://localhost:8000/schedule/generate

    Safe to leave wired up permanently — has no effect when dev_mode=false.
    """
    if settings.dev_mode and settings.dev_api_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            if token == settings.dev_api_token:
                # Mark request as dev-authenticated so future auth dependencies
                # can check request.state.dev_authenticated
                request.state.dev_authenticated = True
            else:
                # Wrong token provided — reject immediately even in dev mode
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid dev token."},
                )

    response = await call_next(request)
    return response


app.include_router(health.router)
app.include_router(solver.router)


@app.get("/")
async def root():
    return {
        "message": "Schedula Schedule Solver API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
