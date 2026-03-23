"""MongoDB async client singleton using PyMongo async API."""

from __future__ import annotations

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from app.config import settings

_db_client: AsyncMongoClient | None = None
_db: AsyncDatabase | None = None


async def init_db() -> None:
    """Initialize MongoDB connection."""
    global _db_client, _db

    _db_client = AsyncMongoClient(settings.mongodb_uri)
    _db = _db_client[settings.mongodb_db_name]

    try:
        await _db_client.admin.command("ping")
        print(f"✓ MongoDB connected: {settings.mongodb_db_name}")
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        raise


async def close_db() -> None:
    """Close MongoDB connection."""
    global _db_client

    if _db_client:
        await _db_client.aclose()
        print("✓ MongoDB connection closed")


def get_db() -> AsyncDatabase:
    """Get MongoDB database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db
