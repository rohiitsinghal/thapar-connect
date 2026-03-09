"""
API route handlers for the timetable system.

Endpoints:
  POST /generate-timetable        — run the solver and persist results
  GET  /batch/{batch_id}/timetable
  GET  /teacher/{teacher_id}/timetable
  GET  /room/{room_id}/timetable
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import GenerateRequest, GenerateResponse, TimetableEntryResponse
from app.services.solver   import run_solver
from app.services.optimizer import (
    persist_timetable,
    get_entries_for_batch,
    get_entries_for_teacher,
    get_entries_for_room,
)
from app.models.models import Batch, Teacher, Room
from app.core.config import settings
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-timetable", response_model=GenerateResponse)
def generate_timetable(
    request: GenerateRequest = GenerateRequest(),
    db: Session = Depends(get_db),
):
    """
    Run the full solver pipeline:
      1. Load entities from the database.
      2. Build a hard-constraint-valid initial timetable.
      3. Optimise using local search.
      4. Persist the best timetable found.
      5. Return summary statistics.
    """
    # Allow per-request iteration override
    if request.iterations is not None:
        settings.SOLVER_ITERATIONS = request.iterations

    try:
        placements, penalty = run_solver(db)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    entries = persist_timetable(db, placements)

    return GenerateResponse(
        message       = "Timetable generated and saved successfully.",
        total_entries = len(entries),
        penalty_score = penalty,
    )


@router.get("/batch/{batch_id}/timetable", response_model=List[TimetableEntryResponse])
def get_batch_timetable(batch_id: int, db: Session = Depends(get_db)):
    """Return all scheduled lectures for a given batch, ordered by day and slot."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

    entries = get_entries_for_batch(db, batch_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No timetable found for this batch. Run /generate-timetable first."
        )
    return entries


@router.get("/teacher/{teacher_id}/timetable", response_model=List[TimetableEntryResponse])
def get_teacher_timetable(teacher_id: int, db: Session = Depends(get_db)):
    """Return all scheduled lectures for a given teacher."""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher {teacher_id} not found.")

    entries = get_entries_for_teacher(db, teacher_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No timetable found for this teacher. Run /generate-timetable first."
        )
    return entries


@router.get("/room/{room_id}/timetable", response_model=List[TimetableEntryResponse])
def get_room_timetable(room_id: int, db: Session = Depends(get_db)):
    """Return all scheduled lectures for a given room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found.")

    entries = get_entries_for_room(db, room_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No timetable found for this room. Run /generate-timetable first."
        )
    return entries