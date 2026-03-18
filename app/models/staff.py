"""Staff model."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal, Optional


class Staff(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    department_id: str
    name: str = Field(max_length=100)
    email: EmailStr
    role: Literal["professor", "ta"]
    faculty_id: Optional[str] = None
