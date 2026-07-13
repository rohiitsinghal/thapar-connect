"""Student authentication (login + change password) backed by DynamoDB.

Passwords are stored in DynamoDB as bcrypt hashes, never in plaintext.
A successful login returns a short-lived JWT that the frontend must send
back as `Authorization: Bearer <token>` when changing the password.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth_core import check_password, get_item_or_404, issue_token, set_password, subject_from_token
from db import get_students_table

ROLE = "student"

router = APIRouter(prefix="/auth/student", tags=["student-auth"])


class LoginPayload(BaseModel):
    roll_no: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=5)


def _normalize_roll_no(roll_no: str) -> str:
    return roll_no.strip().upper()


def _public_profile(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "roll_no": item.get("roll_no"),
        "name": item.get("name"),
        "email": item.get("email"),
        "major": item.get("major"),
        "minor": item.get("minor"),
        "must_change_password": bool(item.get("password_is_default", False)),
    }


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    roll_no = _normalize_roll_no(payload.roll_no)
    item = get_item_or_404(get_students_table(), "roll_no", roll_no, "No student found for that roll number")

    if not check_password(item, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect roll number or password")

    return {"token": issue_token(roll_no, ROLE), **_public_profile(item)}


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, authorization: str = Header(default="")) -> dict[str, Any]:
    roll_no = subject_from_token(authorization, ROLE)
    item = get_item_or_404(get_students_table(), "roll_no", roll_no, "No student found for that roll number")

    if not check_password(item, payload.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    set_password(get_students_table(), "roll_no", roll_no, payload.new_password)
    return {"status": "ok"}
