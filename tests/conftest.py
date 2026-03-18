"""Pytest fixtures and test configuration."""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.main import app
from app.config import settings


@pytest.fixture
async def test_client():
    """FastAPI test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def mock_db():
    """Mock MongoDB database."""
    # TODO: Create mock Motor database for testing
    pass


@pytest.fixture
def solver_weights():
    """Default solver weights."""
    return {
        "break_window": 100,
        "consecutive_slots": 80,
        "session_spread": 60,
        "campus_clustering": 40,
    }
