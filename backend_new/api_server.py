"""FastAPI wrapper around the timetable generation pipeline.

The frontend talks to this API to publish semester dates, trigger a fresh
generation, and read the latest timetable JSON.
"""

from __future__ import annotations

import io
import json
import os
import sys
import contextlib
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from admin_auth import router as admin_auth_router
from auth import router as student_auth_router
from course_material import router as course_material_router
from faculty_auth import router as faculty_auth_router
from main import (
    ACTIVE_PARITY,
    DATA_DIR,
    EXTRACTED_JSON,
    MASTER_TIMETABLE_XLSX,
    OUTPUT_DIR,
    REQUIRED_DATA_FILES,
    TIMETABLE_JSON,
    generate_timetable,
)
from master_sync import import_master_timetable
from genMaster import build_master
from test import run_tests

SETTINGS_JSON = os.path.join(OUTPUT_DIR, "timetable_publish_settings.json")

DEFAULT_SEMESTER_WEEKS = 16


@contextlib.asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    from rds import ensure_schema

    try:
        ensure_schema()
    except Exception as exc:  # noqa: BLE001 - startup should not crash the whole API over RDS being unreachable
        print(f"Warning: could not verify/create course_materials table in RDS: {exc}")

    yield


app = FastAPI(title="Thapar Connect Timetable API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student_auth_router)
app.include_router(faculty_auth_router)
app.include_router(admin_auth_router)
app.include_router(course_material_router)


class PublishSettingsPayload(BaseModel):
    semester_weeks: int = Field(ge=1, le=52)
    semester_start_date: str
    semester_end_date: str


class GenerateTimetablePayload(BaseModel):
    active_parity: Optional[str] = Field(default=None, pattern="^(even|odd)$")
    initial_temp: Optional[float] = Field(default=None, gt=0)
    cooling_rate: Optional[float] = Field(default=None, gt=0)
    min_temp: Optional[float] = Field(default=None, gt=0)
    iters_per_temp: Optional[int] = Field(default=None, ge=1)
    restart_threshold: Optional[int] = Field(default=None, ge=1)
    polish_iters: Optional[int] = Field(default=None, ge=0)


def _ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _data_files_status() -> dict[str, Any]:
    status = {name: os.path.exists(path) for name, path in REQUIRED_DATA_FILES.items()}
    status["all_present"] = all(status.values())
    return status


async def _save_upload(field_name: str, upload: UploadFile) -> None:
    if field_name not in REQUIRED_DATA_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown data file field '{field_name}'")
    if not upload.filename or not upload.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail=f"'{field_name}' must be an .xlsx file (got '{upload.filename}')",
        )
    _ensure_data_dir()
    dest_path = REQUIRED_DATA_FILES[field_name]
    contents = await upload.read()
    with open(dest_path, "wb") as handle:
        handle.write(contents)


@app.get("/timetable-data/status")
def timetable_data_status() -> dict[str, Any]:
    """Which of the 5 required uploaded files are currently on disk."""
    return _data_files_status()


@app.post("/timetable-data/upload")
async def upload_timetable_data(
    students: Optional[UploadFile] = File(default=None),
    curriculum: Optional[UploadFile] = File(default=None),
    teacher_name: Optional[UploadFile] = File(default=None),
    teachers: Optional[UploadFile] = File(default=None),
    rooms: Optional[UploadFile] = File(default=None),
) -> dict[str, Any]:
    """Accepts any subset of the 5 required data files (field name is what
    matters — the original filename the admin picked is irrelevant) and
    saves each into the fixed data/ path main.py expects."""
    provided = {
        "students": students,
        "curriculum": curriculum,
        "teacher_name": teacher_name,
        "teachers": teachers,
        "rooms": rooms,
    }
    saved = []
    for field_name, upload in provided.items():
        if upload is not None:
            await _save_upload(field_name, upload)
            saved.append(field_name)

    if not saved:
        raise HTTPException(status_code=400, detail="No files were provided")

    return {"saved": saved, "status": _data_files_status()}


def _load_publish_settings() -> dict[str, Any]:
    if not os.path.exists(SETTINGS_JSON):
        return {
            "semester_weeks": DEFAULT_SEMESTER_WEEKS,
            "semester_start_date": "",
            "semester_end_date": "",
            "published_at": "",
        }

    with open(SETTINGS_JSON, encoding="utf-8") as handle:
        payload = json.load(handle)

    return {
        "semester_weeks": int(payload.get("semester_weeks", DEFAULT_SEMESTER_WEEKS)),
        "semester_start_date": str(payload.get("semester_start_date", "")),
        "semester_end_date": str(payload.get("semester_end_date", "")),
        "published_at": str(payload.get("published_at", "")),
    }


def _save_publish_settings(settings: PublishSettingsPayload) -> dict[str, Any]:
    _ensure_output_dir()
    payload = {
        "semester_weeks": settings.semester_weeks,
        "semester_start_date": settings.semester_start_date,
        "semester_end_date": settings.semester_end_date,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(SETTINGS_JSON, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload


def _load_timetable() -> dict[str, Any]:
    if not os.path.exists(TIMETABLE_JSON):
        raise HTTPException(status_code=404, detail="Timetable has not been generated yet")

    with open(TIMETABLE_JSON, encoding="utf-8") as handle:
        return json.load(handle)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/timetable-settings/publish")
def get_publish_settings() -> dict[str, Any]:
    return _load_publish_settings()


@app.post("/timetable-settings/publish")
def publish_settings(payload: PublishSettingsPayload) -> dict[str, Any]:
    return _save_publish_settings(payload)


@app.post("/timetable/generate")
def generate(payload: GenerateTimetablePayload) -> dict[str, Any]:
    selected_parity = payload.active_parity or ACTIVE_PARITY
    sa_params: dict[str, Any] = {}

    for key in (
        "initial_temp",
        "cooling_rate",
        "min_temp",
        "iters_per_temp",
        "restart_threshold",
        "polish_iters",
    ):
        value = getattr(payload, key)
        if value is not None:
            sa_params[key] = value

    status = _data_files_status()
    if not status["all_present"]:
        missing = [name for name in REQUIRED_DATA_FILES if not status[name]]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate: missing uploaded file(s): {', '.join(missing)}",
        )

    try:
        timetable = generate_timetable(active_parity=selected_parity, sa_params=sa_params)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "generated",
        "active_parity": selected_parity,
        "timetable": timetable,
        "publish_settings": _load_publish_settings(),
        "artifacts": {
            "extracted_json": EXTRACTED_JSON,
            "timetable_json": TIMETABLE_JSON,
            "master_timetable_xlsx": MASTER_TIMETABLE_XLSX,
        },
    }


@app.get("/timetable/latest")
def latest_timetable() -> dict[str, Any]:
    return _load_timetable()


@app.get("/timetable/student/{enrollment_no}")
def student_timetable(enrollment_no: str) -> dict[str, Any]:
    timetable = _load_timetable()
    student = timetable.get("by_student", {}).get(enrollment_no)
    if not student:
        raise HTTPException(status_code=404, detail="Student timetable not found")
    return student


@app.get("/timetable/master")
def master_timetable() -> FileResponse:
    if not os.path.exists(MASTER_TIMETABLE_XLSX):
        raise HTTPException(status_code=404, detail="Master timetable has not been generated yet")
    return FileResponse(
        MASTER_TIMETABLE_XLSX,
        filename="master_timetable.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/timetable/master")
async def upload_master_timetable(file: UploadFile = File(...)) -> dict[str, Any]:
    """Admin re-uploads master_timetable.xlsx (same file downloaded via
    GET /timetable/master, possibly hand-edited). Parses it, rewrites
    timetable.json, regenerates the styled xlsx, and runs test.py so we
    know whether the edit broke any hard constraints."""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail=f"Must be an .xlsx file (got '{file.filename}')")

    _ensure_output_dir()
    tmp_path = os.path.join(OUTPUT_DIR, "_uploaded_master_timetable.xlsx")
    contents = await file.read()
    with open(tmp_path, "wb") as handle:
        handle.write(contents)

    try:
        timetable = import_master_timetable(tmp_path, EXTRACTED_JSON, TIMETABLE_JSON)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    build_master(timetable, MASTER_TIMETABLE_XLSX)

    # Run test.py against the rebuilt timetable.json and capture its output.
    report_buffer = io.StringIO()
    with contextlib.redirect_stdout(report_buffer):
        tests_passed = run_tests(TIMETABLE_JSON)

    return {
        "status": "updated_from_manual_upload",
        "timetable": timetable,
        "tests_passed": tests_passed,
        "test_report": report_buffer.getvalue(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)