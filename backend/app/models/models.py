"""
ORM models.

Design notes:
- All primary keys are plain integers (auto-increment) for simplicity.
- TimetableEntry stores day and slot_index as integers — the Timeslot object
  is reconstructed on demand from utils/timeslots.py.
- Foreign-key relationships use lazy="select" (default) which is fine for
  the relatively small datasets a university timetable involves.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)

    # One teacher teaches many subjects
    subjects = relationship("Subject", back_populates="teacher")
    # One teacher appears in many timetable entries
    timetable_entries = relationship("TimetableEntry", back_populates="teacher")


class Room(Base):
    __tablename__ = "rooms"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(60), nullable=False)
    capacity = Column(Integer, nullable=False)

    timetable_entries = relationship("TimetableEntry", back_populates="room")


class Batch(Base):
    __tablename__ = "batches"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), nullable=False)
    size = Column(Integer, nullable=False)   # number of students
    year = Column(Integer, nullable=False)   # e.g. 1, 2, 3, 4

    subjects          = relationship("Subject",        back_populates="batch")
    timetable_entries = relationship("TimetableEntry", back_populates="batch")


class Subject(Base):
    __tablename__ = "subjects"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(120), nullable=False)
    teacher_id       = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    batch_id         = Column(Integer, ForeignKey("batches.id"),   nullable=False)
    lectures_per_week = Column(Integer, nullable=False, default=2)

    teacher = relationship("Teacher", back_populates="subjects")
    batch   = relationship("Batch",   back_populates="subjects")
    timetable_entries = relationship("TimetableEntry", back_populates="subject")


class TimetableEntry(Base):
    """
    One scheduled lecture.

    (day, slot_index) together identify the timeslot.
    We store them as plain integers — the Timeslot VO is recreated from
    utils/timeslots.py whenever display info is needed.

    The three unique constraints mirror the three hard constraints:
      - a teacher can only be in one place at a time
      - a room can only host one class at a time
      - a batch can only attend one class at a time
    """
    __tablename__ = "timetable_entries"

    id         = Column(Integer, primary_key=True, index=True)
    day        = Column(Integer, nullable=False)         # 0=Mon … 4=Fri
    slot_index = Column(Integer, nullable=False)         # 0–10

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    room_id    = Column(Integer, ForeignKey("rooms.id"),    nullable=False)
    batch_id   = Column(Integer, ForeignKey("batches.id"),  nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    teacher = relationship("Teacher", back_populates="timetable_entries")
    room    = relationship("Room",    back_populates="timetable_entries")
    batch   = relationship("Batch",   back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")

    # Database-level enforcement of hard constraints 1, 2, 3
    __table_args__ = (
        UniqueConstraint("teacher_id", "day", "slot_index", name="uq_teacher_slot"),
        UniqueConstraint("room_id",    "day", "slot_index", name="uq_room_slot"),
        UniqueConstraint("batch_id",   "day", "slot_index", name="uq_batch_slot"),
    )