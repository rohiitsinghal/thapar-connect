"""FastAPI wrapper around the timetable generation pipeline.

The frontend talks to this API to publish semester dates, trigger a fresh
generation, and read the latest timetable JSON.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from auth import router as student_auth_router
from faculty_auth import router as faculty_auth_router
from main import (
    ACTIVE_PARITY,
    EXTRACTED_JSON,
    MASTER_TIMETABLE_XLSX,
    OUTPUT_DIR,
    TIMETABLE_JSON,
    generate_timetable,
)

SETTINGS_JSON = os.path.join(OUTPUT_DIR, "timetable_publish_settings.json")

DEFAULT_SEMESTER_WEEKS = 16

app = FastAPI(title="Thapar Connect Timetable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(student_auth_router)
app.include_router(faculty_auth_router)


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

    timetable = generate_timetable(active_parity=selected_parity, sa_params=sa_params)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)