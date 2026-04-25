"""Enrollment model for tracking student enrollments in courses."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class Enrollment(BaseModel):
    """Student enrollment in a course section."""
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    institution_id: str
    term_label: str
    course_id: str = Field(description="Reference to course section ID")
    enrolled_students: int = Field(ge=0, description="Number of students enrolled")
    capacity: int = Field(ge=1, description="Course section capacity")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    @property
    def fill_rate(self) -> float:
        """Calculate fill rate as percentage."""
        if self.capacity == 0:
            return 0.0
        return (self.enrolled_students / self.capacity) * 100


class EnrollmentUpdate(BaseModel):
    """Data for updating enrollment."""
    
    enrolled_students: int = Field(ge=0)
