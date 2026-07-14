"""Course material upload/list/download/delete, backed entirely by RDS
(file bytes + metadata in one MySQL table — see rds.py). Faculty upload
material for a course they teach; students enrolled in that course, the
faculty who teaches it, and admin can view and download it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pymysql
from fastapi import APIRouter, File, Form, Header, HTTPException, Response, UploadFile

from auth_core import claims_from_token, get_item_or_404, subject_from_token
from course_catalog import faculty_teaches_course, student_can_view_course
from db import get_faculty_table, get_students_table
from rds import get_connection

router = APIRouter(prefix="/course-material", tags=["course-material"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".txt", ".png", ".jpg", ".jpeg",
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


def _normalize_course_code(course_code: str) -> str:
    return course_code.strip().upper()


def _authorize_view(course_code: str, authorization: str) -> None:
    claims = claims_from_token(authorization)
    role = claims["role"]
    subject = claims["sub"]

    if role == "admin":
        return

    if role == "faculty":
        faculty_item = get_item_or_404(get_faculty_table(), "employee_code", subject, "Faculty record not found")
        if faculty_teaches_course(course_code, faculty_item):
            return
        raise HTTPException(status_code=403, detail="You do not teach this course")

    if role == "student":
        student_item = get_item_or_404(get_students_table(), "roll_no", subject, "Student record not found")
        if student_can_view_course(course_code, student_item):
            return
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")

    raise HTTPException(status_code=403, detail="Unrecognized role")


def _fetch_material_row(course_code: str, material_id: str) -> dict[str, Any]:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM course_materials WHERE course_code = %s AND material_id = %s",
                    (course_code, material_id),
                )
                row = cursor.fetchone()
    except pymysql.MySQLError as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}") from exc

    if not row:
        raise HTTPException(status_code=404, detail="Material not found")
    return row


@router.post("/{course_code}/upload")
async def upload_material(
    course_code: str,
    title: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    employee_code = subject_from_token(authorization, "faculty")
    faculty_item = get_item_or_404(get_faculty_table(), "employee_code", employee_code, "Faculty record not found")

    normalized_code = _normalize_course_code(course_code)
    if not faculty_teaches_course(normalized_code, faculty_item):
        raise HTTPException(status_code=403, detail="You do not teach this course")

    if not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    filename = file.filename or "material"
    extension = filename[filename.rfind(".") :].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{extension}' is not allowed")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 25 MB limit")

    material_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    content_type = file.content_type or "application/octet-stream"
    uploaded_by_name = faculty_item.get("name", "")

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO course_materials
                        (material_id, course_code, title, file_name, content_type, size_bytes,
                         file_data, uploaded_by, uploaded_by_name, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        material_id,
                        normalized_code,
                        title.strip(),
                        filename,
                        content_type,
                        len(contents),
                        contents,
                        employee_code,
                        uploaded_by_name,
                        uploaded_at,
                    ),
                )
    except pymysql.MySQLError as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}") from exc

    return {
        "material_id": material_id,
        "course_code": normalized_code,
        "title": title.strip(),
        "file_name": filename,
        "content_type": content_type,
        "size_bytes": len(contents),
        "uploaded_by": employee_code,
        "uploaded_by_name": uploaded_by_name,
        "uploaded_at": uploaded_at,
    }


@router.get("/{course_code}")
def list_material(course_code: str, authorization: str = Header(default="")) -> dict[str, Any]:
    normalized_code = _normalize_course_code(course_code)
    _authorize_view(normalized_code, authorization)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT material_id, title, file_name, content_type, size_bytes,
                           uploaded_by, uploaded_by_name, uploaded_at
                    FROM course_materials
                    WHERE course_code = %s
                    ORDER BY uploaded_at DESC
                    """,
                    (normalized_code,),
                )
                rows = cursor.fetchall()
    except pymysql.MySQLError as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}") from exc

    return {"course_code": normalized_code, "materials": rows}


@router.get("/{course_code}/{material_id}/download")
def download_material(course_code: str, material_id: str, authorization: str = Header(default="")) -> Response:
    normalized_code = _normalize_course_code(course_code)
    _authorize_view(normalized_code, authorization)

    row = _fetch_material_row(normalized_code, material_id)
    return Response(
        content=row["file_data"],
        media_type=row["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{row["file_name"]}"'},
    )


@router.delete("/{course_code}/{material_id}")
def delete_material(course_code: str, material_id: str, authorization: str = Header(default="")) -> dict[str, str]:
    claims = claims_from_token(authorization)
    role = claims["role"]
    subject = claims["sub"]
    normalized_code = _normalize_course_code(course_code)

    row = _fetch_material_row(normalized_code, material_id)
    if role != "admin" and row.get("uploaded_by") != subject:
        raise HTTPException(status_code=403, detail="You can only delete material you uploaded")

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM course_materials WHERE course_code = %s AND material_id = %s",
                    (normalized_code, material_id),
                )
    except pymysql.MySQLError as exc:
        raise HTTPException(status_code=502, detail=f"Database error: {exc}") from exc

    return {"status": "deleted"}
