"""Database indexes and initialization."""

from pymongo.asynchronous.database import AsyncDatabase
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)


async def init_indexes(db: AsyncDatabase) -> None:
    """Initialize indexes for all collections."""
    
    try:
        # ====================================================================
        # ENROLLMENTS INDEXES
        # ====================================================================
        await db["enrollments"].create_index(
            [("institution_id", ASCENDING), ("term_label", ASCENDING)],
            name="idx_institution_term",
        )
        
        await db["enrollments"].create_index(
            [("institution_id", ASCENDING), ("term_label", ASCENDING), ("course_id", ASCENDING)],
            name="idx_institution_term_course",
            unique=True,
        )
        
        await db["enrollments"].create_index(
            [("updated_at", DESCENDING)],
            name="idx_updated_at",
        )
        
        logger.info("✓ Enrollments indexes created")
        
        # ====================================================================
        # SCHEDULE REVISIONS INDEXES
        # ====================================================================
        await db["schedule_revisions"].create_index(
            [("institution_id", ASCENDING), ("term_label", ASCENDING)],
            name="idx_institution_term",
        )
        
        await db["schedule_revisions"].create_index(
            [("institution_id", ASCENDING), ("term_label", ASCENDING), ("revision_number", DESCENDING)],
            name="idx_institution_term_revision",
        )
        
        await db["schedule_revisions"].create_index(
            [("published_at", DESCENDING)],
            name="idx_published_at",
        )
        
        logger.info("✓ Schedule Revisions indexes created")
        
        # ====================================================================
        # CONFLICT RESOLUTIONS INDEXES
        # ====================================================================
        await db["conflict_resolutions"].create_index(
            [("institution_id", ASCENDING), ("term_label", ASCENDING)],
            name="idx_institution_term",
        )
        
        await db["conflict_resolutions"].create_index(
            [("schedule_revision_id", ASCENDING)],
            name="idx_schedule_revision_id",
        )
        
        await db["conflict_resolutions"].create_index(
            [("conflict_type", ASCENDING)],
            name="idx_conflict_type",
        )
        
        await db["conflict_resolutions"].create_index(
            [("resolved_at", DESCENDING)],
            name="idx_resolved_at",
        )
        
        logger.info("✓ Conflict Resolutions indexes created")
        
    except Exception as e:
        logger.error(f"Failed to initialize indexes: {e}")
        raise
