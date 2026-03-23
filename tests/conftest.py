"""Pytest fixtures and test configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def test_client():
    """FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def mock_db():
    """Mock MongoDB database."""
    # TODO: Create mock PyMongo async database for testing (mock AsyncDatabase)
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
