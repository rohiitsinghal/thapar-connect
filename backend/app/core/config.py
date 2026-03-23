"""
Application configuration — reads every tunable value from environment
variables (or the .env file via python-dotenv).

All academic-structure numbers, solver parameters, and room counts live
here.  Nothing else in the codebase hard-codes these values.

Adding a new variable:
  1. Add it to .env with a comment explaining its purpose.
  2. Add a corresponding field here with a sensible default.
  3. Reference it anywhere via `from app.core.config import settings`.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/tiet_timetable"

    # ── Academic structure ────────────────────────────────────────────
    ACADEMIC_YEARS:                  int = 4
    SEMESTERS_PER_YEAR:              int = 2   # → 8 total semesters for BTech
    SUBJECTS_PER_BATCH_PER_SEMESTER: int = 5
    LECTURES_PER_WEEK_CORE:          int = 3
    LECTURES_PER_WEEK_ELECTIVE:      int = 2

    # ── Departments ───────────────────────────────────────────────────
    # Stored as a comma-separated string in .env; parsed to a list here.
    ACTIVE_DEPARTMENTS: str = "COE,ECE,MEE,CHE,CIE,ELE,AIML,ENC"

    @property
    def active_department_list(self) -> List[str]:
        return [d.strip() for d in self.ACTIVE_DEPARTMENTS.split(",") if d.strip()]

    # ── Batch sizes ───────────────────────────────────────────────────
    SECTION_SPLIT_THRESHOLD: int = 180   # above this → split into A + B

    INTAKE_COE:  int = 960
    INTAKE_ECE:  int = 240
    INTAKE_MEE:  int = 120
    INTAKE_CHE:  int = 60
    INTAKE_CIE:  int = 90
    INTAKE_ELE:  int = 90
    INTAKE_AIML: int = 240
    INTAKE_ENC:  int = 360

    @property
    def intake_map(self) -> dict:
        """dept_code → annual intake (total across all years)."""
        return {
            "COE":  self.INTAKE_COE,
            "ECE":  self.INTAKE_ECE,
            "MEE":  self.INTAKE_MEE,
            "CHE":  self.INTAKE_CHE,
            "CIE":  self.INTAKE_CIE,
            "ELE":  self.INTAKE_ELE,
            "AIML": self.INTAKE_AIML,
            "ENC":  self.INTAKE_ENC,
        }

    # ── Room inventory ────────────────────────────────────────────────
    ROOMS_300: int = 5
    ROOMS_180: int = 4
    ROOMS_120: int = 4
    ROOMS_60:  int = 5
    ROOMS_40:  int = 4
    ROOMS_30:  int = 3
    ROOMS_25:  int = 5

    # ── Solver ────────────────────────────────────────────────────────
    SOLVER_MAX_RETRIES: int   = 15
    SOLVER_ITERATIONS:  int   = 20000
    SA_T_START:         float = 300.0
    SA_T_END:           float = 0.1

    # ── Timeslots ─────────────────────────────────────────────────────
    DAY_START_MINUTES: int = 480   # 08:00
    LECTURE_DURATION:  int = 50
    SLOTS_PER_DAY:     int = 11

    # ── Output ────────────────────────────────────────────────────────
    PRINT_TIMETABLE_CONSOLE: bool = True
    LOG_LEVEL:               str  = "INFO"

    class Config:
        env_file = ".env"
        extra    = "ignore"


settings = Settings()