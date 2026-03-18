"""Schedule output model."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ScheduleEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: str
    day_of_week: int
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    room_id: str
    assigned_staff: list[str]


class ScheduleSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    institution_id: str
    term_label: str
    generated_at: datetime
    entries: list[ScheduleEntry] = Field(default=[])
    hard_violations: int
    soft_penalty_total: float
    warnings: list[str] = Field(default=[])
