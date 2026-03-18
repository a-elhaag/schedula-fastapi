"""Staff availability model."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import time


class PreferredBreakWindow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time


class Availability(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    staff_id: str
    term_label: str
    weekly_day_off: Optional[int] = Field(
        None, ge=0, le=6, description="0=Monday (hard constraint, fully blocked)"
    )
    preferred_break_windows: list[PreferredBreakWindow] = Field(default=[])
    submitted_at: Optional[str] = None
