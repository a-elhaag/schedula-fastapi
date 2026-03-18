"""Solver request/response models."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class SolverWeights(BaseModel):
    break_window: int = Field(default=100, ge=0)
    consecutive_slots: int = Field(default=80, ge=0)
    session_spread: int = Field(default=60, ge=0)
    campus_clustering: int = Field(default=40, ge=0)


class GenerateScheduleRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_id: str
    term_label: str
    weights: Optional[SolverWeights] = None
