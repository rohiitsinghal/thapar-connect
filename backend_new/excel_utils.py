"""Small helpers shared by import_students.py and import_faculty.py for reading
loosely-structured Excel rosters (inconsistent headers, sparse/blank padding rows)."""

from __future__ import annotations

from typing import Any, Optional


def normalize_header(value: Any) -> str:
    return str(value or "").strip().lower()


def find_column(headers: list[Any], candidates: set[str]) -> Optional[int]:
    for index, header in enumerate(headers):
        if normalize_header(header) in candidates:
            return index
    return None


def cell(row: tuple[Any, ...], index: Optional[int]) -> str:
    if index is None or index >= len(row) or row[index] is None:
        return ""
    return str(row[index]).strip()
