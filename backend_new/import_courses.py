"""Import the course catalog into DynamoDB.

Unlike import_students.py/import_faculty.py, this doesn't re-parse the
workbook itself — it reuses course_catalog.get_course_catalog(), which
already implements the exact same parsing rules used to authorize
course-material access, so there's a single source of truth for what a
"course" looks like.

Usage:
    python import_courses.py
    python import_courses.py --dry-run
"""

from __future__ import annotations

import os
import sys

from botocore.exceptions import ClientError
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

import argparse  # noqa: E402

from course_catalog import get_course_catalog  # noqa: E402
from db import get_courses_table  # noqa: E402


def import_courses(dry_run: bool = False) -> None:
    catalog = get_course_catalog()
    print(f"Parsed {len(catalog)} courses from the workbook")

    if dry_run:
        for course in catalog[:5]:
            print(course)
        print("Dry run: nothing was written to DynamoDB.")
        return

    table = get_courses_table()
    written = 0
    for course in catalog:
        try:
            table.put_item(
                Item={
                    "course_code": course["courseCode"],
                    "semester": str(course["semester"]),
                    "title": course["title"],
                    "credits": course["credits"],
                    "facultyName": course["facultyName"],
                    "facultyCode": course["facultyCode"],
                    "programs": course["programs"],
                    "categories": course["categories"],
                }
            )
        except ClientError as exc:
            print(f"Failed to write {course['courseCode']} (sem {course['semester']}): {exc}")
            continue

        written += 1

    print(f"Done. Wrote/updated {written} courses in DynamoDB table '{table.table_name}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the course catalog into DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print a sample without writing to DynamoDB")
    args = parser.parse_args()

    import_courses(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
