"""Course section model."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional


class CourseSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    department_id: str
    course_name: str = Field(max_length=100)
    section_type: Literal["lecture", "lab", "tutorial"]
    year_levels: list[int] = Field(description="e.g. [2] or [3, 4] for electives")
    slots_per_week: int = Field(ge=1, le=7)
    slot_duration_minutes: Optional[int] = None
    capacity: int = Field(ge=1)
    required_room_label: Optional[str] = None
    assigned_staff: list[str] = Field(default=[], description="Staff IDs assigned to this section")
    shared_with: list[str] = Field(
        default=[],
        description="Department IDs attending this lecture (lecture only)",
    )

    @field_validator("year_levels")
    @classmethod
    def validate_year_levels(cls, v):
        if not v or any(y < 1 for y in v):
            raise ValueError("year_levels must be non-empty positive integers")
        return sorted(list(set(v)))

    @field_validator("shared_with")
    @classmethod
    def validate_shared_with(cls, v, info):
        if info.data.get("section_type") != "lecture" and v:
            raise ValueError("Only lecture sections can have shared_with")
        return v
