"""
Configuration management using Pydantic Settings.
Reads environment variables or falls back to defaults (useful for local dev).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL connection URL
    # Format: postgresql://user:password@host:port/dbname
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/timetable_db"

    # Solver parameters — exposed here so they can be tuned without touching code
    SOLVER_ITERATIONS: int = 1000   # number of local-search moves to attempt
    SOLVER_MAX_RETRIES: int = 5     # retries for initial random assignment

    class Config:
        env_file = ".env"           # load from .env file if present


# Singleton instance imported everywhere
settings = Settings()