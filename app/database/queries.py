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
            "_id": 0,
            "break_window": 1, "consecutive_slots": 1,
            "session_spread": 1, "campus_clustering": 1,
        },
    )


# ============================================================================
# ENROLLMENT QUERIES
# ============================================================================

async def get_enrollment(
    db: AsyncDatabase, institution_id: str, term_label: str, course_id: str
) -> dict[str, Any] | None:
    """Get enrollment for a specific course."""
    return await db["enrollments"].find_one(
        {"institution_id": institution_id, "term_label": term_label, "course_id": course_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "course_id": 1,
            "enrolled_students": 1, "capacity": 1, "created_at": 1, "updated_at": 1,
        },
    )


async def get_enrollments(
    db: AsyncDatabase, institution_id: str, term_label: str
) -> list[dict[str, Any]]:
    """Get all enrollments for a term."""
    return await db["enrollments"].find(
        {"institution_id": institution_id, "term_label": term_label, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "course_id": 1,
            "enrolled_students": 1, "capacity": 1, "created_at": 1, "updated_at": 1,
        },
    ).to_list(None)


async def create_enrollment(
    db: AsyncDatabase, enrollment_data: dict[str, Any]
) -> str:
    """Create a new enrollment record. Returns enrollment ID."""
    result = await db["enrollments"].insert_one(enrollment_data)
    return str(result.inserted_id)


async def update_enrollment(
    db: AsyncDatabase,
    institution_id: str,
    term_label: str,
    course_id: str,
    update_data: dict[str, Any],
) -> bool:
    """Update enrollment. Returns True if found and updated."""
    from datetime import datetime
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db["enrollments"].update_one(
        {"institution_id": institution_id, "term_label": term_label, "course_id": course_id, **_SOFT_DELETE},
        {"$set": update_data},
    )
    return result.matched_count > 0


async def delete_enrollment(
    db: AsyncDatabase, institution_id: str, term_label: str, course_id: str
) -> bool:
    """Soft delete an enrollment. Returns True if found."""
    from datetime import datetime
    result = await db["enrollments"].update_one(
        {"institution_id": institution_id, "term_label": term_label, "course_id": course_id, **_SOFT_DELETE},
        {"$set": {"deleted_at": datetime.utcnow()}},
    )
    return result.matched_count > 0


# ============================================================================
# SCHEDULE REVISION QUERIES
# ============================================================================

async def get_schedule_revision(
    db: AsyncDatabase, institution_id: str, term_label: str, revision_number: int
) -> dict[str, Any] | None:
    """Get a specific schedule revision."""
    return await db["schedule_revisions"].find_one(
        {"institution_id": institution_id, "term_label": term_label, "revision_number": revision_number, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "revision_number": 1,
            "published_at": 1, "published_by": 1, "entries": 1,
            "hard_violations": 1, "soft_penalty_total": 1, "warnings": 1, "notes": 1,
        },
    )


async def get_latest_schedule_revision(
    db: AsyncDatabase, institution_id: str, term_label: str
) -> dict[str, Any] | None:
    """Get the latest (highest revision number) schedule."""
    revisions = await db["schedule_revisions"].find(
        {"institution_id": institution_id, "term_label": term_label, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "revision_number": 1,
            "published_at": 1, "published_by": 1, "entries": 1,
            "hard_violations": 1, "soft_penalty_total": 1, "warnings": 1, "notes": 1,
        },
        sort=[("revision_number", -1)],
    ).to_list(1)
    
    return revisions[0] if revisions else None


async def get_schedule_revisions(
    db: AsyncDatabase, institution_id: str, term_label: str
) -> list[dict[str, Any]]:
    """Get all schedule revisions for a term, ordered by revision number (newest first)."""
    return await db["schedule_revisions"].find(
        {"institution_id": institution_id, "term_label": term_label, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "revision_number": 1,
            "published_at": 1, "published_by": 1, "hard_violations": 1,
            "soft_penalty_total": 1, "notes": 1,
        },
        sort=[("revision_number", -1)],
    ).to_list(None)


async def create_schedule_revision(
    db: AsyncDatabase, revision_data: dict[str, Any]
) -> str:
    """Create a new schedule revision. Returns revision ID."""
    result = await db["schedule_revisions"].insert_one(revision_data)
    return str(result.inserted_id)


async def delete_schedule_revision(
    db: AsyncDatabase, institution_id: str, term_label: str, revision_number: int
) -> bool:
    """Soft delete a schedule revision. Returns True if found."""
    from datetime import datetime
    result = await db["schedule_revisions"].update_one(
        {"institution_id": institution_id, "term_label": term_label, "revision_number": revision_number, **_SOFT_DELETE},
        {"$set": {"deleted_at": datetime.utcnow()}},
    )
    return result.matched_count > 0


# ============================================================================
# CONFLICT RESOLUTION QUERIES
# ============================================================================

async def get_conflict_resolution(
    db: AsyncDatabase, conflict_id: str
) -> dict[str, Any] | None:
    """Get a specific conflict resolution."""
    return await db["conflict_resolutions"].find_one(
        {"_id": conflict_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "schedule_revision_id": 1,
            "conflict_type": 1, "affected_sections": 1, "description": 1,
            "resolution_action": 1, "resolved_by": 1, "resolved_at": 1, "notes": 1,
        },
    )


async def get_conflict_resolutions_for_schedule(
    db: AsyncDatabase, schedule_revision_id: str
) -> list[dict[str, Any]]:
    """Get all conflicts resolved for a specific schedule revision."""
    return await db["conflict_resolutions"].find(
        {"schedule_revision_id": schedule_revision_id, **_SOFT_DELETE},
        projection={
            "_id": 1, "institution_id": 1, "term_label": 1, "conflict_type": 1,
            "affected_sections": 1, "description": 1, "resolution_action": 1,
            "resolved_by": 1, "resolved_at": 1,
        },
    ).to_list(None)


async def get_conflict_resolutions_by_term(
    db: AsyncDatabase, institution_id: str, term_label: str
) -> list[dict[str, Any]]:
    """Get all conflict resolutions for a term."""
    return await db["conflict_resolutions"].find(
        {"institution_id": institution_id, "term_label": term_label, **_SOFT_DELETE},
        projection={
            "_id": 1, "schedule_revision_id": 1, "conflict_type": 1,
            "affected_sections": 1, "description": 1, "resolution_action": 1,
            "resolved_by": 1, "resolved_at": 1,
        },
    ).to_list(None)


async def create_conflict_resolution(
    db: AsyncDatabase, conflict_data: dict[str, Any]
) -> str:
    """Create a new conflict resolution record. Returns conflict ID."""
    result = await db["conflict_resolutions"].insert_one(conflict_data)
    return str(result.inserted_id)


async def delete_conflict_resolution(db: AsyncDatabase, conflict_id: str) -> bool:
    """Soft delete a conflict resolution. Returns True if found."""
    from datetime import datetime
    result = await db["conflict_resolutions"].update_one(
        {"_id": conflict_id, **_SOFT_DELETE},
        {"$set": {"deleted_at": datetime.utcnow()}},
    )
    return result.matched_count > 0
