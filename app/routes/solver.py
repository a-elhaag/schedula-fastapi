"""Solver route — schedule generation endpoint."""

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.asynchronous.database import AsyncDatabase

from app.config import settings
from app.database.client import get_db
from app.database.queries import (
    get_availability,
    get_constraints,
    get_courses,
    get_institution,
    get_rooms,
    get_staff,
)
from app.models.solver import GenerateScheduleRequest
from app.services.solver_service import ScheduleSolver

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/generate", response_model=dict)
async def generate_schedule(
    request: GenerateScheduleRequest,
    db: AsyncDatabase = Depends(get_db),
):
    """
    Generate a constraint-based timetable for the institution.

    Reads all data from MongoDB, runs OR-Tools CP-SAT solver, returns snapshot.
    FastAPI never writes — Next.js persists the snapshot after coordinator approval.
    """
    try:
        institution = await get_institution(db, request.institution_id)
        if not institution:
            raise HTTPException(
                status_code=404,
                detail=f"Institution {request.institution_id} not found",
            )

        # Parallel fetch — all collections at once
        courses, staff, availability, rooms, db_constraints = await asyncio.gather(
            get_courses(db, request.institution_id),
            get_staff(db, request.institution_id),
            get_availability(db, request.institution_id, request.term_label),
            get_rooms(db, request.institution_id),
            get_constraints(db, request.institution_id),
        )

        if not courses:
            raise HTTPException(status_code=400, detail="No courses found for this institution")

        # Soft constraint weights: request > DB > config defaults
        weights = {
            "break_window": settings.soft_weight_break_window,
            "consecutive_slots": settings.soft_weight_consecutive_slots,
            "session_spread": settings.soft_weight_session_spread,
            "campus_clustering": settings.soft_weight_campus_clustering,
        }
        if db_constraints:
            weights.update({k: v for k, v in db_constraints.items() if k in weights and v is not None})
        if request.weights:
            weights["break_window"] = request.weights.break_window
            weights["consecutive_slots"] = request.weights.consecutive_slots
            weights["session_spread"] = request.weights.session_spread
            weights["campus_clustering"] = request.weights.campus_clustering

        solver = ScheduleSolver(
            time_limit_seconds=settings.solver_time_limit_seconds,
            num_workers=settings.solver_num_workers,
        )
        solver.build_model(
            institution_data=institution,
            courses_data=courses,
            staff_data=staff,
            availability_data=availability,
            rooms_data=rooms,
            weights=weights,
        )

        hard_violations, soft_penalty, schedule_entries = solver.solve()

        warnings = []
        if hard_violations > 0:
            warnings.append(f"Schedule has {hard_violations} hard constraint violations")
        if soft_penalty > 1000:
            warnings.append(f"High soft penalty: {soft_penalty:.0f}")
        if not schedule_entries:
            warnings.append("No feasible schedule found")

        return {
            "snapshot_id": str(uuid.uuid4()),
            "institution_id": request.institution_id,
            "term_label": request.term_label,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": schedule_entries,
            "hard_violations": hard_violations,
            "soft_penalty": soft_penalty,
            "warnings": warnings,
            "summary": {
                "total_sections": len(courses),
                "scheduled_sections": len({e["section_id"] for e in schedule_entries}),
                "total_staff": len(staff),
                "total_rooms": len(rooms),
                "weights": weights,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")
