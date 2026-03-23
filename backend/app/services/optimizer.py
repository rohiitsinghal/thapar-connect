"""
Optimizer service — bridges solver output and the database.

Changes from previous version
──────────────────────────────
  persist_timetable : now accepts `semester` int, stores it on every entry,
                      and clears only that semester's entries (not all).
  _log_timetable_to_console : new grouping — dept → semester → batch.
"""

import logging
from collections import defaultdict
from typing      import List

from sqlalchemy.orm import Session

from app.models.models  import TimetableEntry, Teacher, Room, Batch, Subject
from app.services.scoring import Placement
from app.schemas.schemas  import TimetableEntryResponse
from app.utils.timeslots  import DAYS, DAY_START_MINUTES, LECTURE_DURATION
from app.core.config      import settings

logger = logging.getLogger(__name__)


# ── Time helpers ──────────────────────────────────────────────────────────────

def _slot_to_time(slot_index: int) -> tuple[str, str]:
    start = DAY_START_MINUTES + slot_index * LECTURE_DURATION
    end   = start + LECTURE_DURATION
    sh, sm = divmod(start, 60)
    eh, em = divmod(end,   60)
    return f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}"


# ── Console display ───────────────────────────────────────────────────────────

def _log_timetable_to_console(entries: list, semester: int) -> None:
    """
    Print the timetable grouped by:
        Department  →  Semester  →  Batch  →  Day  →  Slot

    Output format:
        ╔══════════════════════════════════════╗
          DEPARTMENT: COE   SEMESTER: 1
        ╚══════════════════════════════════════╝

          BATCH: COE-Y1-A  (15 lectures this week)
          ─────────────────────────────────────
            Monday
              08:00 - 08:50  │  Programming Fundamentals
                             │  Prof. Rajesh Kumar Sharma  │  A-LH1
    """
    if not settings.PRINT_TIMETABLE_CONSOLE:
        return

    # Group entries: dept → batch_name → day → [entry]
    by_dept: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for entry in entries:
        dept = entry.batch.department
        by_dept[dept][entry.batch.name][entry.day].append(entry)

    W = 70
    print(f"\n{'X' * W}")
    print(f"  GENERATED TIMETABLE — SEMESTER {semester}")
    print(f"{'X' * W}")

    for dept in sorted(by_dept.keys()):
        print(f"\n{'#' * W}")
        print(f"  DEPARTMENT: {dept}   SEMESTER: {semester}")
        print(f"{'#' * W}")

        batch_dict = by_dept[dept]
        for batch_name in sorted(batch_dict.keys()):
            day_dict     = batch_dict[batch_name]
            total_lec    = sum(len(v) for v in day_dict.values())

            print(f"\n  {'=' * (W - 2)}")
            print(f"  BATCH: {batch_name}  ({total_lec} lectures this week)")
            print(f"  {'=' * (W - 2)}")

            for day_idx in range(5):
                day_entries = sorted(day_dict.get(day_idx, []),
                                     key=lambda e: e.slot_index)
                if not day_entries:
                    continue

                print(f"\n    {DAYS[day_idx]}")
                print(f"    {'-' * (W - 4)}")
                for entry in day_entries:
                    start, end = _slot_to_time(entry.slot_index)
                    print(f"    {start} - {end}  │  {entry.subject.name}")
                    print(f"    {' ' * 13}  │  {entry.teacher.name:<28}  │  {entry.room.name}")
                print(f"    {'-' * (W - 4)}")

    print(f"\n{'X' * W}")
    print(f"  SEMESTER {semester} — Total scheduled lectures : {len(entries)}")
    print(f"{'X' * W}\n")


# ── Persistence ───────────────────────────────────────────────────────────────

def persist_timetable(
    db:        Session,
    placements: List[Placement],
    semester:  int,
) -> List[TimetableEntry]:
    """
    Wipe the current semester's timetable entries and persist a new set.

    Only entries for `semester` are deleted — other semesters are untouched.
    """
    deleted = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.semester == semester)
        .delete()
    )
    logger.info(f"Cleared {deleted} existing entries for semester {semester}.")

    entries = [
        TimetableEntry(
            semester   = semester,
            day        = p.day,
            slot_index = p.slot,
            teacher_id = p.teacher_id,
            room_id    = p.room_id,
            batch_id   = p.batch_id,
            subject_id = p.subject_id,
        )
        for p in placements
    ]

    db.add_all(entries)
    db.commit()

    for entry in entries:
        db.refresh(entry)

    logger.info(f"Persisted {len(entries)} entries for semester {semester}.")

    if settings.PRINT_TIMETABLE_CONSOLE:
        _log_timetable_to_console(entries, semester)

    return entries


# ── Response builders ─────────────────────────────────────────────────────────

def build_entry_response(entry: TimetableEntry) -> TimetableEntryResponse:
    start_time, end_time = _slot_to_time(entry.slot_index)
    return TimetableEntryResponse(
        id           = entry.id,
        semester     = entry.semester,
        day          = entry.day,
        slot_index   = entry.slot_index,
        day_name     = DAYS[entry.day],
        start_time   = start_time,
        end_time     = end_time,
        teacher_id   = entry.teacher_id,
        teacher_name = entry.teacher.name,
        room_id      = entry.room_id,
        room_name    = entry.room.name,
        batch_id     = entry.batch_id,
        batch_name   = entry.batch.name,
        department   = entry.batch.department,
        subject_id   = entry.subject_id,
        subject_name = entry.subject.name,
    )


def get_entries_for_semester(
    db: Session, semester: int
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.semester == semester)
        .order_by(TimetableEntry.batch_id, TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_batch(
    db: Session, batch_id: int, semester: int
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.batch_id  == batch_id,
            TimetableEntry.semester  == semester,
        )
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_room(
    db: Session, room_id: int, semester: int
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.room_id  == room_id,
            TimetableEntry.semester == semester,
        )
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_teacher(
    db: Session, teacher_id: int, semester: int
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.teacher_id == teacher_id,
            TimetableEntry.semester   == semester,
        )
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_department(
    db: Session, department: str, semester: int
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .join(Batch, TimetableEntry.batch_id == Batch.id)
        .filter(
            Batch.department         == department,
            TimetableEntry.semester  == semester,
        )
        .order_by(TimetableEntry.batch_id, TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]