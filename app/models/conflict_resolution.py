"""Conflict resolution model for tracking resolved schedule conflicts."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional


class ConflictResolution(BaseModel):
    """Resolution of a schedule conflict."""
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    term_label: str
    schedule_revision_id: str = Field(description="Reference to schedule revision")
    conflict_type: Literal[
        "room_overlap",
        "instructor_overlap", 
        "capacity_exceeded",
        "room_feature_missing",
        "time_slot_unavailable",
        "other"
    ]
    affected_sections: list[str] = Field(description="IDs of sections involved in conflict")
    description: str = Field(description="Human-readable description of conflict")
    resolution_action: str = Field(
        description="Action taken to resolve (e.g., 'moved_to_different_room', 'changed_time_slot')"
    )
    resolved_by: str = Field(description="User ID who resolved conflict")
    resolved_at: datetime
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
