"""Faculty authentication (login + change password) backed by DynamoDB.

Mirrors auth.py (student), keyed by employee_code instead of roll_no.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth_core import check_password, get_item_or_404, issue_token, set_password, subject_from_token
from db import get_faculty_table

ROLE = "faculty"

router = APIRouter(prefix="/auth/faculty", tags=["faculty-auth"])


class LoginPayload(BaseModel):
    employee_code: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=5)


def _normalize_employee_code(employee_code: str) -> str:
    return employee_code.strip()


def _public_profile(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "employee_code": item.get("employee_code"),
        "teacher_code": item.get("teacher_code"),
        "name": item.get("name"),
        "designation": item.get("designation"),
        "email": item.get("email"),
        "must_change_password": bool(item.get("password_is_default", False)),
    }


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    employee_code = _normalize_employee_code(payload.employee_code)
    item = get_item_or_404(
        get_faculty_table(), "employee_code", employee_code, "No faculty member found for that employee code"
    )

    if not check_password(item, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect employee code or password")

    return {"token": issue_token(employee_code, ROLE), **_public_profile(item)}


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, authorization: str = Header(default="")) -> dict[str, Any]:
    employee_code = subject_from_token(authorization, ROLE)
    item = get_item_or_404(
        get_faculty_table(), "employee_code", employee_code, "No faculty member found for that employee code"
    )

    if not check_password(item, payload.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    set_password(get_faculty_table(), "employee_code", employee_code, payload.new_password)
    return {"status": "ok"}
