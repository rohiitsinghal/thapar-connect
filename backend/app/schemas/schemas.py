"""
Pydantic schemas — request/response DTOs.
"""

from pydantic import BaseModel
from typing   import Optional


class TimetableEntryResponse(BaseModel):
    id:           int
    semester:     int
    day:          int
    slot_index:   int
    day_name:     str
    start_time:   str
    end_time:     str
    teacher_id:   int
    teacher_name: str
    room_id:      int
    room_name:    str
    batch_id:     int
    batch_name:   str
    department:   str
    subject_id:   int
    subject_name: str

    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    semester:       int
    penalty_score:  int
    lectures_count: int
    message:        str