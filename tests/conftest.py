"""Pytest fixtures and test configuration."""

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient

from app.main import app

# Configure pytest-asyncio for async fixtures and tests
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for tests."""
    import asyncio
    return asyncio.get_event_loop_policy()


@pytest.fixture
async def test_client():
    """FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def mock_db():
    """Mock MongoDB async database."""
    db = AsyncMock()
    # Mock the ping command for readiness checks
    db.command = AsyncMock(return_value=None)
    return db


@pytest.fixture
def solver_weights():
    """Default solver weights."""
    return {
        "break_window": 100,
        "consecutive_slots": 80,
        "session_spread": 60,
        "campus_clustering": 40,
    }
