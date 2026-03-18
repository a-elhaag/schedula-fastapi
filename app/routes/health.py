"""Health check routes."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check (includes MongoDB connection)."""
    from app.database.client import get_db

    try:
        db = get_db()
        # Quick ping to verify DB is accessible
        await db.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e),
        }, 503
