"""Admin authentication.

Admin has no DynamoDB-backed profile — it's a single fixed account configured
via env vars. This exists purely so admin, like student/faculty, gets a JWT
that course-material endpoints can authorize against, mirroring the
`admin@thapar.edu` / `qwertyuiop` credentials already hardcoded client-side
in Login.tsx.
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from auth_core import issue_token

ROLE = "admin"

router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])


class LoginPayload(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


def _admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "admin@thapar.edu")


def _admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "qwertyuiop")


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, str]:
    email_matches = payload.email.strip().lower() == _admin_email().strip().lower()
    password_matches = hmac.compare_digest(payload.password, _admin_password())

    if not email_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Incorrect admin email or password")

    return {"token": issue_token(_admin_email(), ROLE)}
