"""
Pydantic schemas for API request validation and response serialisation.

We keep input schemas (Create) separate from output schemas (Response) so
that auto-generated fields (ids, computed strings) don't bleed into inputs.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional


# ---------------------------------------------------------------------------
# Base / shared
# ---------------------------------------------------------------------------

class TeacherBase(BaseModel):
    name: str

class TeacherCreate(TeacherBase):
    pass

class TeacherResponse(TeacherBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RoomBase(BaseModel):
    name: str
    capacity: int

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BatchBase(BaseModel):
    name: str
    size: int
    year: int

class BatchCreate(BatchBase):
    pass

class BatchResponse(BatchBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SubjectBase(BaseModel):
    name: str
    teacher_id: int
    batch_id: int
    lectures_per_week: int = 2

class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Timetable entry — the core output schema
# ---------------------------------------------------------------------------

class TimetableEntryResponse(BaseModel):
    """
    A single scheduled lecture, enriched with human-readable strings.
    The day_name and time fields are computed from day + slot_index.
    """
    id:         int
    day:        int
    slot_index: int
    day_name:   str           # e.g. "Monday"
    start_time: str           # e.g. "08:00"
    end_time:   str           # e.g. "08:50"
    teacher_id: int
    teacher_name: str
    room_id:    int
    room_name:  str
    batch_id:   int
    batch_name: str
    subject_id: int
    subject_name: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Solver / generation
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """
    Optional parameters to tune the solver at call time.
    Falls back to values in config.py if not provided.
    """
    iterations: Optional[int] = None

class GenerateResponse(BaseModel):
    message:        str
    total_entries:  int
    penalty_score:  int         # lower = better timetable