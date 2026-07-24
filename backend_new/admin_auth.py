
from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth_core import check_password, issue_token, set_password, subject_from_token
from db import get_admin_table

ROLE = "admin"

router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])


class LoginPayload(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=5)


def _admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "admin@thapar.edu")


def _admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "qwertyuiop")


def _get_admin_item(email: str) -> dict[str, Any] | None:
    response = get_admin_table().get_item(Key={"email": email})
    return response.get("Item")


def _password_matches(email: str, password: str) -> bool:
    item = _get_admin_item(email)
    if item and item.get("password_hash"):
        return check_password(item, password)
    # No override stored yet — fall back to the env-configured password.
    return hmac.compare_digest(password, _admin_password())


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, str]:
    email = payload.email.strip().lower()
    admin_email = _admin_email().strip().lower()

    if email != admin_email or not _password_matches(admin_email, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect admin email or password")

    return {"token": issue_token(admin_email, ROLE)}


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, authorization: str = Header(default="")) -> dict[str, Any]:
    admin_email = subject_from_token(authorization, ROLE)

    if not _password_matches(admin_email, payload.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Admin table may not have a row yet (first-ever password change) —
    # set_password's update_item will create one if it doesn't exist.
    set_password(get_admin_table(), "email", admin_email, payload.new_password)
    return {"status": "ok"}