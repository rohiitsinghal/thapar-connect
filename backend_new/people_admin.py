"""Admin-only directory management: list/search, Excel upload, and inline
edits for the student and faculty DynamoDB tables.

Upload reuses the parsing/write logic in import_students.py / import_faculty.py
by writing the uploaded workbook to a temp file and calling those functions
directly, so both the CLI scripts and this API stay in sync.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from auth_core import claims_from_token
from db import get_faculty_table, get_students_table
from import_faculty import import_faculty
from import_students import import_students

router = APIRouter(prefix="/admin/people", tags=["admin-people"])

STUDENT_EDITABLE_FIELDS = {"name", "email", "major", "minor"}
FACULTY_EDITABLE_FIELDS = {"name", "teacher_code", "designation", "email"}


class UpdateFieldsPayload(BaseModel):
    fields: dict[str, str]


def _require_admin(authorization: str) -> None:
    claims = claims_from_token(authorization)
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _scan_all(table: Any) -> list[dict[str, Any]]:
    try:
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc
    return items


def _update_fields(table: Any, key_name: str, key_value: str, fields: dict[str, str], allowed: set[str]) -> dict[str, Any]:
    updates = {name: value for name, value in fields.items() if name in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail=f"No editable fields provided (allowed: {sorted(allowed)})")

    expression_names = {f"#{name}": name for name in updates}
    expression_values = {f":{name}": value for name, value in updates.items()}
    set_clause = ", ".join(f"#{name} = :{name}" for name in updates)

    try:
        response = table.update_item(
            Key={key_name: key_value},
            UpdateExpression=f"SET {set_clause}",
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc

    return response.get("Attributes", {})


def _delete_item(table: Any, key_name: str, key_value: str) -> None:
    try:
        response = table.delete_item(Key={key_name: key_value}, ReturnValues="ALL_OLD")
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc

    if not response.get("Attributes"):
        raise HTTPException(status_code=404, detail="Record not found")


@router.get("/students")
def list_students(authorization: str = Header(default="")) -> dict[str, Any]:
    _require_admin(authorization)
    students = _scan_all(get_students_table())
    students.sort(key=lambda item: item.get("roll_no") or "")
    return {"students": students}


@router.get("/faculty")
def list_faculty(authorization: str = Header(default="")) -> dict[str, Any]:
    _require_admin(authorization)
    faculty = _scan_all(get_faculty_table())
    faculty.sort(key=lambda item: item.get("employee_code") or "")
    return {"faculty": faculty}


@router.post("/students/upload")
async def upload_students(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization)
    contents = await file.read()

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        written = import_students(tmp_path, default_password="12345")
    except Exception as exc:  # noqa: BLE001 - surfaced to the admin as an upload error
        raise HTTPException(status_code=400, detail=f"Could not import workbook: {exc}") from exc
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    students = _scan_all(get_students_table())
    return {"written": written, "count": len(students)}


@router.post("/faculty/upload")
async def upload_faculty(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization)
    contents = await file.read()

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        written = import_faculty(tmp_path, default_password="tiet12345")
    except Exception as exc:  # noqa: BLE001 - surfaced to the admin as an upload error
        raise HTTPException(status_code=400, detail=f"Could not import workbook: {exc}") from exc
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    faculty = _scan_all(get_faculty_table())
    return {"written": written, "count": len(faculty)}


@router.put("/students/{roll_no}")
def update_student(roll_no: str, payload: UpdateFieldsPayload, authorization: str = Header(default="")) -> dict[str, Any]:
    _require_admin(authorization)
    updated = _update_fields(get_students_table(), "roll_no", roll_no, payload.fields, STUDENT_EDITABLE_FIELDS)
    return {"student": updated}


@router.put("/faculty/{employee_code}")
def update_faculty(employee_code: str, payload: UpdateFieldsPayload, authorization: str = Header(default="")) -> dict[str, Any]:
    _require_admin(authorization)
    updated = _update_fields(get_faculty_table(), "employee_code", employee_code, payload.fields, FACULTY_EDITABLE_FIELDS)
    return {"faculty": updated}


@router.delete("/students/{roll_no}")
def delete_student(roll_no: str, authorization: str = Header(default="")) -> dict[str, str]:
    _require_admin(authorization)
    _delete_item(get_students_table(), "roll_no", roll_no)
    return {"roll_no": roll_no}


@router.delete("/faculty/{employee_code}")
def delete_faculty(employee_code: str, authorization: str = Header(default="")) -> dict[str, str]:
    _require_admin(authorization)
    _delete_item(get_faculty_table(), "employee_code", employee_code)
    return {"employee_code": employee_code}
