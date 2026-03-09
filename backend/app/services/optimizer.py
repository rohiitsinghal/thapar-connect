"""
Optimizer service — bridges the solver output and the database.

Responsibilities:
  1. Clear any existing timetable (so each generate call is idempotent).
  2. Convert Placement objects → TimetableEntry ORM objects.
  3. Bulk-insert into PostgreSQL.
  4. Build the enriched response DTOs used by the API layer.

This separation keeps solver.py free of any SQLAlchemy/ORM concerns so the
solver can be unit-tested with plain Python objects.
"""

import logging
from typing import List, Dict

from sqlalchemy.orm import Session

from app.models.models import TimetableEntry, Teacher, Room, Batch, Subject
from app.services.scoring import Placement
from app.schemas.schemas import TimetableEntryResponse
from app.utils.timeslots import DAYS, DAY_START_MINUTES, LECTURE_DURATION

logger = logging.getLogger(__name__)


def _slot_to_time(slot_index: int) -> tuple[str, str]:
    """Convert a slot index to (start_time, end_time) strings."""
    start = DAY_START_MINUTES + slot_index * LECTURE_DURATION
    end   = start + LECTURE_DURATION
    sh, sm = divmod(start, 60)
    eh, em = divmod(end, 60)
    return f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}"


def _log_timetable_to_console(entries: list) -> None:
    """
    Prints the full generated timetable to the console, grouped by batch,
    then by day, then by slot — so you see one complete batch schedule
    before moving on to the next.

    Output format:
        BATCH : CS-Year1-A  (12 lectures this week)
          Monday
            08:00 - 08:50  |  Subject: Intro to Programming
                           |  Teacher: Dr. Alice Mercer  |  Room: LH-101
          Tuesday
            ...

    TO DISABLE: comment out the _log_timetable_to_console(entries) call
    in persist_timetable() just above the return statement.
    """
    from collections import defaultdict
    from app.utils.timeslots import DAYS

    # ── Step 1: group entries by batch_id ────────────────────────────────────
    by_batch: dict = defaultdict(list)
    for entry in entries:
        by_batch[entry.batch_id].append(entry)

    print("\n")
    print("X" * 70)
    print("  GENERATED TIMETABLE  (batch-wise view)")
    print("X" * 70)

    # ── Step 2: iterate batches in consistent order ───────────────────────────
    for batch_id in sorted(by_batch.keys()):
        batch_entries = by_batch[batch_id]
        batch_name    = batch_entries[0].batch.name

        print(f"\n{'=' * 70}")
        print(f"  BATCH : {batch_name}  ({len(batch_entries)} lectures this week)")
        print(f"{'=' * 70}")

        # ── Step 3: group this batch's entries by day ─────────────────────────
        by_day: dict = defaultdict(list)
        for entry in batch_entries:
            by_day[entry.day].append(entry)

        # ── Step 4: iterate days Monday to Friday ─────────────────────────────
        for day_index in range(5):
            day_entries = by_day.get(day_index, [])
            if not day_entries:
                continue

            day_entries.sort(key=lambda e: e.slot_index)

            print(f"\n    {DAYS[day_index]}")
            print(f"    {'-' * 62}")

            for entry in day_entries:
                start, end = _slot_to_time(entry.slot_index)
                print(f"    {start} - {end}  |  Subject: {entry.subject.name}")
                print(f"    {' ' * 13}  |  Teacher: {entry.teacher.name:<22}  |  Room: {entry.room.name}")

            print(f"    {'-' * 62}")

    print(f"\n{'X' * 70}")
    print(f"  Total scheduled lectures : {len(entries)}")
    print(f"{'X' * 70}\n")


def persist_timetable(
    db: Session,
    placements: List[Placement],
) -> List[TimetableEntry]:
    """
    Wipe the current timetable and persist a new one.

    We use a bulk insert (add_all) rather than individual commits for
    performance — a typical semester has 200–400 entries.
    """
    # Clear existing timetable
    deleted = db.query(TimetableEntry).delete()
    logger.info(f"Cleared {deleted} existing timetable entries.")

    # Build ORM objects
    entries = [
        TimetableEntry(
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

    # Refresh to get auto-assigned IDs back
    for entry in entries:
        db.refresh(entry)

    logger.info(f"Persisted {len(entries)} timetable entries.")

    # ──────────────────────────────────────────────────────────────────────────
    # CONSOLE TIMETABLE DISPLAY — comment out this entire block when not needed
    # ──────────────────────────────────────────────────────────────────────────
    _log_timetable_to_console(entries)
    # ──────────────────────────────────────────────────────────────────────────

    return entries


def build_entry_response(entry: TimetableEntry) -> TimetableEntryResponse:
    """
    Enrich a TimetableEntry ORM object with human-readable fields.
    Assumes all relationships (teacher, room, batch, subject) are loaded.
    """
    start_time, end_time = _slot_to_time(entry.slot_index)

    return TimetableEntryResponse(
        id          = entry.id,
        day         = entry.day,
        slot_index  = entry.slot_index,
        day_name    = DAYS[entry.day],
        start_time  = start_time,
        end_time    = end_time,
        teacher_id  = entry.teacher_id,
        teacher_name= entry.teacher.name,
        room_id     = entry.room_id,
        room_name   = entry.room.name,
        batch_id    = entry.batch_id,
        batch_name  = entry.batch.name,
        subject_id  = entry.subject_id,
        subject_name= entry.subject.name,
    )


def get_entries_for_batch(
    db: Session,
    batch_id: int,
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.batch_id == batch_id)
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_teacher(
    db: Session,
    teacher_id: int,
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.teacher_id == teacher_id)
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]


def get_entries_for_room(
    db: Session,
    room_id: int,
) -> List[TimetableEntryResponse]:
    entries = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.room_id == room_id)
        .order_by(TimetableEntry.day, TimetableEntry.slot_index)
        .all()
    )
    return [build_entry_response(e) for e in entries]