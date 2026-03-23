"""
ORM models.

Changes from previous version
──────────────────────────────
  Batch   : + department  (str, e.g. "COE", "ECE") — used for console
              grouping and API filtering.
  Subject : + semester    (int, 1–8) — which semester this subject belongs
              to.  The solver filters by semester so each run is isolated.
            + subject_type ("core" | "elective") — drives lectures_per_week
              default in the seed; stored for display purposes.

Everything else is unchanged — the three UniqueConstraints on
TimetableEntry still enforce the hard scheduling constraints at DB level.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(120), nullable=False)
    department = Column(String(20),  nullable=False)   # e.g. "COE"

    subjects          = relationship("Subject",        back_populates="teacher")
    timetable_entries = relationship("TimetableEntry", back_populates="teacher")


class Room(Base):
    __tablename__ = "rooms"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(60),  nullable=False)
    capacity = Column(Integer,     nullable=False)

    timetable_entries = relationship("TimetableEntry", back_populates="room")


class Batch(Base):
    __tablename__ = "batches"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(60), nullable=False)   # e.g. "COE-Y1-A"
    department = Column(String(20), nullable=False)   # e.g. "COE"
    size       = Column(Integer,    nullable=False)   # number of students
    year       = Column(Integer,    nullable=False)   # 1–4

    subjects          = relationship("Subject",        back_populates="batch")
    timetable_entries = relationship("TimetableEntry", back_populates="batch")


class Subject(Base):
    __tablename__ = "subjects"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(120), nullable=False)
    subject_type      = Column(String(20),  nullable=False, default="core")
                        # "core" = 3 lec/week, "elective" = 2 lec/week
    semester          = Column(Integer,     nullable=False)
                        # 1–8 following TIET odd/even convention:
                        #   Year 1 → Sem 1 (odd) and Sem 2 (even)
                        #   Year 2 → Sem 3 and Sem 4  … and so on.
    lectures_per_week = Column(Integer,     nullable=False, default=3)
    teacher_id        = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    batch_id          = Column(Integer, ForeignKey("batches.id"),  nullable=False)

    teacher           = relationship("Teacher", back_populates="subjects")
    batch             = relationship("Batch",   back_populates="subjects")
    timetable_entries = relationship("TimetableEntry", back_populates="subject")


class TimetableEntry(Base):
    """
    One scheduled lecture.

    Unique constraints enforce the three core hard constraints:
      - a teacher can only be in one place at a time
      - a room can only host one class at a time
      - a batch can only attend one class at a time

    Note: because the solver runs per-semester, entries from different
    semesters never compete for the same (day, slot) — they are stored
    together but were scheduled in isolation.
    """
    __tablename__ = "timetable_entries"

    id         = Column(Integer, primary_key=True, index=True)
    semester   = Column(Integer, nullable=False)         # 1–8, mirrors Subject.semester
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

    __table_args__ = (
        UniqueConstraint("teacher_id", "day", "slot_index", "semester", name="uq_teacher_slot_sem"),
        UniqueConstraint("room_id",    "day", "slot_index", "semester", name="uq_room_slot_sem"),
        UniqueConstraint("batch_id",   "day", "slot_index", "semester", name="uq_batch_slot_sem"),
    )