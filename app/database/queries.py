"""Reusable MongoDB async query functions."""

from pymongo.asynchronous.database import AsyncDatabase
from typing import Any


_SOFT_DELETE = {"deleted_at": None}


async def get_institution(db: AsyncDatabase, institution_id: str) -> dict[str, Any] | None:
    return await db["institutions"].find_one(
        {"_id": institution_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "name": 1, "slug": 1,
            "working_days": 1, "daily_start_hour": 1,
            "daily_end_hour": 1, "slot_duration_minutes": 1,
        },
    )


async def get_courses(db: AsyncDatabase, institution_id: str) -> list[dict[str, Any]]:
    return await db["courses"].find(
        {"institution_id": institution_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "department_id": 1,
            "course_name": 1, "section_type": 1, "year_levels": 1,
            "slots_per_week": 1, "slot_duration_minutes": 1,
            "capacity": 1, "required_room_label": 1, "shared_with": 1,
            "assigned_staff": 1,
        },
    ).to_list(None)


async def get_staff(db: AsyncDatabase, institution_id: str) -> list[dict[str, Any]]:
    return await db["users"].find(
        {"institution_id": institution_id, "role": {"$in": ["professor", "ta"]}, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "department_id": 1,
            "name": 1, "email": 1, "role": 1, "faculty_id": 1,
        },
    ).to_list(None)


async def get_availability(
    db: AsyncDatabase, institution_id: str, term_label: str
) -> list[dict[str, Any]]:
    return await db["availability"].find(
        {"institution_id": institution_id, "term_label": term_label, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "staff_id": 1, "term_label": 1,
            "weekly_day_off": 1, "preferred_break_windows": 1,
        },
    ).to_list(None)


async def get_rooms(db: AsyncDatabase, institution_id: str) -> list[dict[str, Any]]:
    return await db["rooms"].find(
        {"institution_id": institution_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "faculty_id": 1,
            "name": 1, "label": 1, "capacity": 1, "features": 1,
        },
    ).to_list(None)


async def get_constraints(db: AsyncDatabase, institution_id: str) -> dict[str, Any] | None:
    """Get soft constraint weights for an institution."""
    return await db["constraints"].find_one(
        {"institution_id": institution_id, **_SOFT_DELETE},
        projection={
            "break_window": 1, "consecutive_slots": 1,
            "session_spread": 1, "campus_clustering": 1,
        },
    )
