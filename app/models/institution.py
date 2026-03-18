"""Institution model."""

from pydantic import BaseModel, ConfigDict, Field


class Institution(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    name: str
    slug: str
    working_days: list[int] = Field(default=[0, 1, 2, 3, 4], description="0=Monday, 4=Friday")
    daily_start_hour: int = Field(default=9)
    daily_end_hour: int = Field(default=17)
    slot_duration_minutes: int = Field(default=60)
