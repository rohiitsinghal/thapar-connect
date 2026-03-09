"""
Application entry point.

Creates the FastAPI app, sets up middleware/logging, creates database tables
on startup, and registers all route groups.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.api.routes.timetable import router as timetable_router

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="University Timetable Scheduler",
    description=(
        "Constraint-based timetable generation system inspired by UniTime. "
        "Uses local-search optimisation to satisfy hard and soft constraints."
    ),
    version="1.0.0",
)

# Allow all origins for development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Create all database tables if they don't exist yet."""
    logger.info("Creating database tables…")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(timetable_router, tags=["Timetable"])


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "docs":   "/docs",
        "redoc":  "/redoc",
    }