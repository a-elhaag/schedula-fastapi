"""Schedule revision model for version control of schedules."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ScheduleEntry(BaseModel):
    """A single schedule entry (class session)."""
    
    section_id: str
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str = Field(description="HH:MM format")
    end_time: str = Field(description="HH:MM format")
    room_id: str
    assigned_staff: list[str] = Field(default=[])


class ScheduleRevision(BaseModel):
    """Version of a published schedule."""
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    term_label: str
    revision_number: int = Field(ge=1, description="Version number of this schedule")
    published_at: datetime
    published_by: str = Field(description="User ID who published")
    entries: list[ScheduleEntry] = Field(default=[])
    hard_violations: int = Field(ge=0)
    soft_penalty_total: float = Field(ge=0)
    warnings: list[str] = Field(default=[])
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    @property
    def is_feasible(self) -> bool:
        """Check if schedule is feasible (no hard violations)."""
        return self.hard_violations == 0
