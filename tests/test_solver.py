"""Basic tests for solver service."""

import pytest
from app.services.solver_service import ScheduleSolver


@pytest.mark.asyncio
async def test_solver_initialization():
    """Test ScheduleSolver can be initialized."""
    solver = ScheduleSolver(time_limit_seconds=30)
    assert solver.time_limit_seconds == 30
    assert solver.model is not None


def test_solver_time_slot_generation():
    """Test time slot generation."""
    solver = ScheduleSolver()

    institution = {
        "daily_start_hour": 9,
        "daily_end_hour": 17,
        "slot_duration_minutes": 60,
    }
    solver.institution_data = institution
    solver._generate_time_slots()

    assert len(solver.time_slots) == 8  # 9am to 5pm = 8 one-hour slots
    assert solver.time_slots[0] == "09:00"
    assert solver.time_slots[-1] == "16:00"
