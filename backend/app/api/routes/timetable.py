"""
API routes — timetable generation and retrieval.

New endpoints vs previous version
───────────────────────────────────
  POST /generate-timetable/{semester}
      Runs the solver for a single semester (1–8) and persists results.
      Returns a summary with penalty score and lecture count.

  POST /generate-timetable/all
      Convenience: runs the solver for every semester sequentially (1→8).
      Returns a summary per semester.

  GET  /timetable/{semester}
      All entries for a semester, grouped by dept in the response.

  GET  /timetable/{semester}/batch/{batch_id}
  GET  /timetable/{semester}/room/{room_id}
  GET  /timetable/{semester}/teacher/{teacher_id}
  GET  /timetable/{semester}/department/{dept_code}
      Filtered views.
"""

from fastapi            import APIRouter, Depends, HTTPException
from sqlalchemy.orm     import Session
from typing             import List

from app.core.database    import get_db
from app.core.config      import settings
from app.services.solver   import run_solver
from app.services.optimizer import (
    persist_timetable,
    get_entries_for_semester,
    get_entries_for_batch,
    get_entries_for_room,
    get_entries_for_teacher,
    get_entries_for_department,
)
from app.schemas.schemas import TimetableEntryResponse, GenerateResponse

router = APIRouter()

TOTAL_SEMESTERS = settings.ACADEMIC_YEARS * settings.SEMESTERS_PER_YEAR


def _valid_semester(semester: int) -> None:
    if semester < 1 or semester > TOTAL_SEMESTERS:
        raise HTTPException(
            status_code=400,
            detail=f"Semester must be between 1 and {TOTAL_SEMESTERS}."
        )


# ── Generation ────────────────────────────────────────────────────────────────

@router.post("/generate-timetable/{semester}", response_model=GenerateResponse)
def generate_semester(semester: int, db: Session = Depends(get_db)):
    """Run the solver for a single semester and persist the result."""
    _valid_semester(semester)
    placements, penalty = run_solver(db, semester=semester)
    entries = persist_timetable(db, placements, semester=semester)
    return GenerateResponse(
        semester       = semester,
        penalty_score  = penalty,
        lectures_count = len(entries),
        message        = (
            f"Semester {semester} scheduled: {len(entries)} lectures, "
            f"penalty={penalty}."
        ),
    )


@router.post("/generate-timetable/all")
def generate_all_semesters(db: Session = Depends(get_db)):
    """Run the solver for all semesters sequentially."""
    results = []
    for sem in range(1, TOTAL_SEMESTERS + 1):
        try:
            placements, penalty = run_solver(db, semester=sem)
            entries = persist_timetable(db, placements, semester=sem)
            results.append({
                "semester":       sem,
                "penalty_score":  penalty,
                "lectures_count": len(entries),
                "status":         "ok",
            })
        except Exception as e:
            results.append({
                "semester": sem,
                "status":   "error",
                "detail":   str(e),
            })
    return {"results": results}


# ── Retrieval ─────────────────────────────────────────────────────────────────

@router.get("/timetable/{semester}", response_model=List[TimetableEntryResponse])
def get_semester_timetable(semester: int, db: Session = Depends(get_db)):
    _valid_semester(semester)
    return get_entries_for_semester(db, semester)


@router.get("/timetable/{semester}/batch/{batch_id}",
            response_model=List[TimetableEntryResponse])
def get_batch_timetable(semester: int, batch_id: int, db: Session = Depends(get_db)):
    _valid_semester(semester)
    return get_entries_for_batch(db, batch_id, semester)


@router.get("/timetable/{semester}/room/{room_id}",
            response_model=List[TimetableEntryResponse])
def get_room_timetable(semester: int, room_id: int, db: Session = Depends(get_db)):
    _valid_semester(semester)
    return get_entries_for_room(db, room_id, semester)


@router.get("/timetable/{semester}/teacher/{teacher_id}",
            response_model=List[TimetableEntryResponse])
def get_teacher_timetable(semester: int, teacher_id: int, db: Session = Depends(get_db)):
    _valid_semester(semester)
    return get_entries_for_teacher(db, teacher_id, semester)


@router.get("/timetable/{semester}/department/{dept_code}",
            response_model=List[TimetableEntryResponse])
def get_department_timetable(semester: int, dept_code: str, db: Session = Depends(get_db)):
    _valid_semester(semester)
    return get_entries_for_department(db, dept_code.upper(), semester)