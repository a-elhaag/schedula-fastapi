"""Room/facility model."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal


class Room(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    faculty_id: str
    name: str = Field(max_length=100)
    label: Optional[str] = Field(None, description="e.g. 'Physics Lab'")
    room_type: Literal["lecture_hall", "tutorial_room", "lab"]
    lab_type: Optional[Literal["computer_lab", "physics_lab", "chemistry_lab", "metal_workshop"]] = None
    groups_capacity: int = Field(ge=1, le=10)
    features: list[str] = Field(default=[], description="e.g. ['projector', 'computers']")
