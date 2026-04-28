"""Solver route — schedule generation endpoint."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

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
    get_enrollments,
)
from app.models.solver import GenerateScheduleRequest, GenerateScheduleResponse
from app.services.solver_service import ScheduleSolver

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["schedule"])


def _resolve_weights(
    request_weights: Any,
    db_constraints: dict[str, Any] | None,
) -> dict[str, int]:
    """Resolve soft constraint weights: request > DB > config defaults."""
    weights = {
        "break_window": settings.soft_weight_break_window,
        "consecutive_slots": settings.soft_weight_consecutive_slots,
        "session_spread": settings.soft_weight_session_spread,
        "campus_clustering": settings.soft_weight_campus_clustering,
    }
    if db_constraints:
        weights.update({k: v for k, v in db_constraints.items() if k in weights and v is not None})
    if request_weights:
        weights["break_window"] = request_weights.break_window
        weights["consecutive_slots"] = request_weights.consecutive_slots
        weights["session_spread"] = request_weights.session_spread
        weights["campus_clustering"] = request_weights.campus_clustering
    return weights


@router.post("/generate", response_model=GenerateScheduleResponse)
async def generate_schedule(
    request: GenerateScheduleRequest,
    db: AsyncDatabase = Depends(get_db),
):
    """
    Generate a constraint-based timetable for the institution.

    Reads all data from MongoDB, runs OR-Tools CP-SAT solver, returns snapshot.
    Validates all hard constraints before attempting to solve.
    FastAPI never writes — Next.js persists the snapshot after coordinator approval.
    """
    try:
        institution = await get_institution(db, request.institution_id)
        if not institution:
            raise HTTPException(
                status_code=404,
                detail=f"Institution {request.institution_id} not found",
            )

        # Normalize institution fields to what the solver expects
        _day_name_to_int = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        _settings = institution.get("settings") or {}
        _active_term = institution.get("active_term") or {}
        _daily_start: str = _settings.get("daily_start", "09:00")
        _daily_end: str = _settings.get("daily_end", "17:00")
        _raw_days = _active_term.get("working_days", [0, 1, 2, 3, 4])
        if _raw_days and isinstance(_raw_days[0], str):
            _raw_days = [_day_name_to_int.get(d.lower(), 0) for d in _raw_days]
        institution_normalized = {
            "_id": institution["_id"],
            "name": institution.get("name", ""),
            "working_days": _raw_days,
            "daily_start_hour": int(_daily_start.split(":")[0]),
            "daily_end_hour": int(_daily_end.split(":")[0]),
            "slot_duration_minutes": _settings.get("slot_duration_minutes", 60),
        }

        # Parallel fetch — all collections at once
        courses, staff, availability, rooms, db_constraints, enrollments_list = await asyncio.gather(
            get_courses(db, request.institution_id),
            get_staff(db, request.institution_id),
            get_availability(db, request.institution_id, request.term_label),
            get_rooms(db, request.institution_id),
            get_constraints(db, request.institution_id),
            get_enrollments(db, request.institution_id, request.term_label),
        )

        if not courses:
            raise HTTPException(status_code=400, detail="No courses found for this institution")

        # Convert enrollments list to dict: course_id -> enrollment data
        enrollments_dict = {}
        for enroll in enrollments_list:
            course_id = enroll["course_id"]
            enrollments_dict[course_id] = {
                "enrolled_students": enroll.get("enrolled_students", 0),
                "capacity": enroll.get("capacity", 0),
            }

        weights = _resolve_weights(request.weights, db_constraints)

        solver = ScheduleSolver(
            time_limit_seconds=settings.solver_time_limit_seconds,
            num_workers=settings.solver_num_workers,
        )
        
        # Build model with validation
        is_feasible, critical_errors, validation_warnings = solver.build_model(
            institution_data=institution_normalized,
            courses_data=courses,
            staff_data=staff,
            availability_data=availability,
            rooms_data=rooms,
            weights=weights,
            section_type_durations=(
                request.section_type_durations.model_dump(exclude_none=True)
                if request.section_type_durations
                else None
            ),
            enrollments_data=enrollments_dict,
        )

        # If validation failed, return error with detailed messages
        if not is_feasible:
            warnings = critical_errors
            return GenerateScheduleResponse(
                snapshot_id=str(uuid.uuid4()),
                institution_id=request.institution_id,
                term_label=request.term_label,
                generated_at=datetime.now(timezone.utc).isoformat(),
                entries=[],
                hard_violations=len(critical_errors),
                soft_penalty=float("inf"),
                warnings=warnings,
                summary={
                    "total_sections": len(courses),
                    "scheduled_sections": 0,
                    "total_staff": len(staff),
                    "total_rooms": len(rooms),
                    "weights": weights,
                    "validation_errors": critical_errors,
                    "validation_warnings": validation_warnings,
                },
            )

        # Solve
        error_code, soft_penalty, schedule_entries, solve_errors = solver.solve()

        warnings = []
        if solve_errors:
            warnings.extend(solve_errors)
        if error_code > 0:
            warnings.append(f"Solver returned error code {error_code}")
        if soft_penalty > 1000:
            warnings.append(f"High soft penalty: {soft_penalty:.0f}")
        if not schedule_entries:
            warnings.append("No feasible schedule found")
        if validation_warnings:
            for constraint, msgs in validation_warnings.items():
                warnings.extend(msgs)

        return GenerateScheduleResponse(
            snapshot_id=str(uuid.uuid4()),
            institution_id=request.institution_id,
            term_label=request.term_label,
            generated_at=datetime.now(timezone.utc).isoformat(),
            entries=schedule_entries,
            hard_violations=error_code,
            soft_penalty=soft_penalty,
            warnings=warnings,
            summary={
                "total_sections": len(courses),
                "scheduled_sections": len({e["section_id"] for e in schedule_entries}),
                "total_staff": len(staff),
                "total_rooms": len(rooms),
                "weights": weights,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Schedule generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")
