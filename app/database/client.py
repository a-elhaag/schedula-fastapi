"""MongoDB async client singleton using PyMongo async API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class _DbState:
    """Internal state holder for database connections."""
    client: AsyncMongoClient | None = None
    db: AsyncDatabase | None = None


_state = _DbState()


async def init_db() -> None:
    """Initialize MongoDB connection."""
    _state.client = AsyncMongoClient(settings.mongodb_uri)
    _state.db = _state.client[settings.mongodb_db_name]

    try:
        await _state.client.admin.command("ping")
        logger.info(f"MongoDB connected: {settings.mongodb_db_name}")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


async def close_db() -> None:
    """Close MongoDB connection."""
    if _state.client:
        await _state.client.aclose()
        logger.info("MongoDB connection closed")


def get_db() -> AsyncDatabase:
    """Get MongoDB database instance."""
    if _state.db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _state.db
