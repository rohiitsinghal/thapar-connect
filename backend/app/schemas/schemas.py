"""
Pydantic schemas — request/response DTOs.
"""

from pydantic import BaseModel, Field
from typing   import Optional
from datetime import date


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


class TimetablePublishSettingsResponse(BaseModel):
    semester_weeks: int = Field(ge=1, le=52)
    semester_start_date: date
    semester_end_date: date
    published_at: Optional[str] = ""


class TimetablePublishSettingsUpdateRequest(BaseModel):
    semester_weeks: int = Field(ge=1, le=52)
    semester_start_date: date
    semester_end_date: date