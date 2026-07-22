"""Course catalog (backed by DynamoDB) and per-course student rosters.

The roster is not an authoritative registration record — no such record
exists anywhere in this system (confirmed: neither the source workbooks nor
the timetable-generation engine store real per-student enrollment). It
reuses the same semester + major/minor matching already used to decide which
courses a student sees as "theirs" (student_can_view_course), applied in
reverse: for a course, which students match it.
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Header, HTTPException

from auth_core import claims_from_token, get_item_or_404
from course_catalog import faculty_teaches_course, student_can_view_course
from db import get_courses_table, get_faculty_table, get_students_table

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_courses() -> dict[str, Any]:
    try:
        response = get_courses_table().scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = get_courses_table().scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc

    items.sort(key=lambda item: (int(item.get("semester", 0)), item.get("course_code", "")))
    return {"courses": items}


@router.get("/{course_code}/roster")
def course_roster(course_code: str, authorization: str = Header(default="")) -> dict[str, Any]:
    claims = claims_from_token(authorization)
    role = claims["role"]
    subject = claims["sub"]
    normalized_code = course_code.strip().upper()

    if role == "faculty":
        faculty_item = get_item_or_404(get_faculty_table(), "employee_code", subject, "Faculty record not found")
        if not faculty_teaches_course(normalized_code, faculty_item):
            raise HTTPException(status_code=403, detail="You do not teach this course")
    elif role != "admin":
        raise HTTPException(status_code=403, detail="Only faculty and admin can view course rosters")

    try:
        response = get_students_table().scan()
        students = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = get_students_table().scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            students.extend(response.get("Items", []))
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"DynamoDB error: {exc}") from exc

    roster = [
        {
            "roll_no": student.get("roll_no"),
            "name": student.get("name"),
            "email": student.get("email"),
            "major": student.get("major"),
            "minor": student.get("minor"),
        }
        for student in students
        if student_can_view_course(normalized_code, student)
    ]
    roster.sort(key=lambda student: student.get("roll_no") or "")

    return {"course_code": normalized_code, "students": roster}
