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
from pathlib            import Path
from datetime           import datetime, timezone, date, timedelta
import json

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
from app.schemas.schemas import (
    TimetableEntryResponse,
    GenerateResponse,
    TimetablePublishSettingsResponse,
    TimetablePublishSettingsUpdateRequest,
)

router = APIRouter()

TOTAL_SEMESTERS = settings.ACADEMIC_YEARS * settings.SEMESTERS_PER_YEAR
DEFAULT_SEMESTER_WEEKS = 16
PUBLISH_SETTINGS_FILE = Path(__file__).resolve().parents[3] / "data" / "timetable_publish_settings.json"


def _normalize_semester_weeks(value: int) -> int:
    return max(1, min(52, int(value)))


def _default_semester_start_date() -> date:
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    return today + timedelta(days=days_until_monday)


def _default_semester_end_date(start_date: date, semester_weeks: int) -> date:
    normalized_weeks = _normalize_semester_weeks(semester_weeks)
    return start_date + timedelta(days=(normalized_weeks * 7) - 1)


def _derive_semester_weeks(start_date: date, end_date: date) -> int:
    span_days = (end_date - start_date).days + 1
    return _normalize_semester_weeks((span_days + 6) // 7)


def _read_publish_settings() -> TimetablePublishSettingsResponse:
    default_start_date = _default_semester_start_date()
    default_end_date = _default_semester_end_date(default_start_date, DEFAULT_SEMESTER_WEEKS)

    if not PUBLISH_SETTINGS_FILE.exists():
        return TimetablePublishSettingsResponse(
            semester_weeks=DEFAULT_SEMESTER_WEEKS,
            semester_start_date=default_start_date,
            semester_end_date=default_end_date,
            published_at="",
        )

    try:
        payload = json.loads(PUBLISH_SETTINGS_FILE.read_text(encoding="utf-8"))

        start_raw = payload.get("semester_start_date")
        end_raw = payload.get("semester_end_date")

        start_date = date.fromisoformat(start_raw) if isinstance(start_raw, str) else default_start_date
        end_date = date.fromisoformat(end_raw) if isinstance(end_raw, str) else _default_semester_end_date(
            start_date,
            _normalize_semester_weeks(payload.get("semester_weeks", DEFAULT_SEMESTER_WEEKS)),
        )

        if end_date < start_date:
            end_date = _default_semester_end_date(start_date, DEFAULT_SEMESTER_WEEKS)

        return TimetablePublishSettingsResponse(
            semester_weeks=_derive_semester_weeks(start_date, end_date),
            semester_start_date=start_date,
            semester_end_date=end_date,
            published_at=payload.get("published_at", "") or "",
        )
    except Exception:
        return TimetablePublishSettingsResponse(
            semester_weeks=DEFAULT_SEMESTER_WEEKS,
            semester_start_date=default_start_date,
            semester_end_date=default_end_date,
            published_at="",
        )


def _write_publish_settings(
    semester_weeks: int,
    semester_start_date: date,
    semester_end_date: date,
) -> TimetablePublishSettingsResponse:
    if semester_end_date < semester_start_date:
        raise HTTPException(status_code=400, detail="Semester end date must be on or after start date.")

    settings_payload = TimetablePublishSettingsResponse(
        semester_weeks=_derive_semester_weeks(semester_start_date, semester_end_date),
        semester_start_date=semester_start_date,
        semester_end_date=semester_end_date,
        published_at=datetime.now(timezone.utc).isoformat(),
    )
    PUBLISH_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_SETTINGS_FILE.write_text(
        json.dumps(settings_payload.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return settings_payload


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


@router.get(
    "/timetable-settings/publish",
    response_model=TimetablePublishSettingsResponse,
)
def get_timetable_publish_settings():
    return _read_publish_settings()


@router.post(
    "/timetable-settings/publish",
    response_model=TimetablePublishSettingsResponse,
)
def update_timetable_publish_settings(payload: TimetablePublishSettingsUpdateRequest):
    return _write_publish_settings(
        semester_weeks=payload.semester_weeks,
        semester_start_date=payload.semester_start_date,
        semester_end_date=payload.semester_end_date,
    )