"""
extractor.py
─────────────────────────────────────────────────────────────────────────────
Reads the 5 Excel input files and builds all in-memory data structures
needed by the scheduler.

Output (all plain Python dicts / lists — no database):
  data["subjects"]           → {subject_code: Subject}
  data["teachers"]           → {teacher_code: Teacher}
  data["rooms"]              → {room_id: Room}
  data["students"]           → {enrollment_no: Student}
  data["curriculum"]         → {(program, semester): [CurriculumEntry]}
  data["teacher_subjects"]   → {subject_code: teacher_code}
  data["enrollment_groups"]  → {(semester, major, minor): [subject_code]}
  data["conflict_graph"]     → {subject_code: set(subject_code)}  ← KEY for scheduler

Usage:
  from extractor import load_data
  data = load_data("path/to/data/")
"""

import pandas as pd
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data classes — typed containers (behave like dicts but with named fields)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Subject:
    subject_code: str
    subject_name: str
    credits: int

    def __repr__(self):
        return f"Subject({self.subject_code}: {self.subject_name})"


@dataclass
class Teacher:
    teacher_code: str
    teacher_name: str
    email: str

    def __repr__(self):
        return f"Teacher({self.teacher_code}: {self.teacher_name})"


@dataclass
class Room:
    room_id: str
    room_name: str
    capacity: int
    room_type: str  # "lecture" | "lab"

    def __repr__(self):
        return f"Room({self.room_id}: {self.room_name}, cap={self.capacity}, {self.room_type})"


@dataclass
class Student:
    enrollment_no: str
    student_name: str
    email: str
    major: str
    minor: str
    semester: int

    def __repr__(self):
        return f"Student({self.enrollment_no}: {self.student_name}, {self.major}/{self.minor}, sem={self.semester})"


@dataclass
class CurriculumEntry:
    program: str
    semester: int
    subject_code: str
    subject_name: str
    credits: int
    offered_as: str  # "major" | "minor" | "both" | "foundation"

    def __repr__(self):
        return f"Curriculum({self.program} sem{self.semester}: {self.subject_code} [{self.offered_as}])"


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def _validate(condition: bool, message: str):
    """Raise a clear ValidationError if condition is False."""
    if not condition:
        raise ValidationError(f"\n  ✗ VALIDATION ERROR: {message}")


def _warn(message: str):
    print(f"  ⚠ WARNING: {message}")


# ─────────────────────────────────────────────────────────────────────────────
# Individual file loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_students(path: str) -> dict[str, Student]:
    """
    Loads students.xlsx
    Columns: enrollment_no | student_name | email | major | minor | semester
    Returns: {enrollment_no: Student}
    """
    print("  Loading students.xlsx ...")
    df = pd.read_excel(path, dtype={"enrollment_no": str})
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"enrollment_no", "student_name", "email", "major", "minor", "semester"}
    _validate(required.issubset(df.columns),
              f"students.xlsx missing columns: {required - set(df.columns)}")

    # Clean strings
    for col in ["enrollment_no", "student_name", "email", "major", "minor"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["semester"] = pd.to_numeric(df["semester"], errors="coerce")

    students = {}
    for _, row in df.iterrows():
        # Validate enrollment number
        _validate(row["enrollment_no"] != "",
                  f"students.xlsx: blank enrollment_no found in row {_ + 2}")

        _validate(row["enrollment_no"] not in students,
                  f"students.xlsx: duplicate enrollment_no '{row['enrollment_no']}'")

        _validate(pd.notna(row["semester"]),
                  f"students.xlsx: invalid semester for student '{row['enrollment_no']}'")

        if row["major"] == "" and int(row["semester"]) > 2:
            _warn(f"Student {row['enrollment_no']} is in sem {int(row['semester'])} but has no major.")

        students[row["enrollment_no"]] = Student(
            enrollment_no = row["enrollment_no"],
            student_name  = row["student_name"],
            email         = row["email"],
            major         = row["major"],
            minor         = row["minor"],
            semester      = int(row["semester"]),
        )

    print(f"    → {len(students)} students loaded.")
    return students


def _load_curriculum(path: str) -> tuple[dict, dict]:
    """
    Loads curriculum.xlsx
    Columns: program | semester | subject_code | subject_name | credits | offered_as
    Returns:
      curriculum  → {(program, semester): [CurriculumEntry]}
      subjects    → {subject_code: Subject}   (derived — single source of truth)
    """
    print("  Loading curriculum.xlsx ...")
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"program", "semester", "subject_code", "subject_name", "credits", "offered_as"}
    _validate(required.issubset(df.columns),
              f"curriculum.xlsx missing columns: {required - set(df.columns)}")

    VALID_ROLES = {"major", "minor", "both", "foundation"}
    for col in ["program", "subject_code", "subject_name", "offered_as"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["semester"] = pd.to_numeric(df["semester"], errors="coerce")
    df["credits"]  = pd.to_numeric(df["credits"],  errors="coerce").fillna(0).astype(int)

    curriculum = defaultdict(list)
    subjects   = {}
    seen       = set()  # track (program, semester, subject_code) for duplicates

    for _, row in df.iterrows():
        _validate(row["program"]       != "", f"curriculum.xlsx row {_ + 2}: blank 'program'")
        _validate(row["subject_code"]  != "", f"curriculum.xlsx row {_ + 2}: blank 'subject_code'")
        _validate(row["offered_as"] in VALID_ROLES,
                  f"curriculum.xlsx row {_ + 2}: invalid offered_as='{row['offered_as']}' "
                  f"(must be one of {VALID_ROLES})")
        _validate(pd.notna(row["semester"]),
                  f"curriculum.xlsx row {_ + 2}: invalid semester value")

        key = (row["program"], int(row["semester"]), row["subject_code"])
        _validate(key not in seen,
                  f"curriculum.xlsx: duplicate row for {key}")
        seen.add(key)

        entry = CurriculumEntry(
            program      = row["program"],
            semester     = int(row["semester"]),
            subject_code = row["subject_code"],
            subject_name = row["subject_name"],
            credits      = row["credits"],
            offered_as   = row["offered_as"],
        )
        curriculum[(row["program"], int(row["semester"]))].append(entry)

        # Build subjects dict — if same code appears twice, name/credits must match
        code = row["subject_code"]
        if code in subjects:
            _validate(
                subjects[code].subject_name == row["subject_name"],
                f"curriculum.xlsx: subject_code '{code}' has inconsistent names: "
                f"'{subjects[code].subject_name}' vs '{row['subject_name']}'"
            )
        else:
            subjects[code] = Subject(
                subject_code = code,
                subject_name = row["subject_name"],
                credits      = row["credits"],
            )

    curriculum = dict(curriculum)
    print(f"    → {len(subjects)} unique subjects, "
          f"{sum(len(v) for v in curriculum.values())} curriculum entries loaded.")
    return curriculum, subjects


def _load_teachers(path: str) -> dict[str, Teacher]:
    """
    Loads teachers.xlsx
    Columns: teacher_code | teacher_name | email
    Returns: {teacher_code: Teacher}
    """
    print("  Loading teachers.xlsx ...")
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"teacher_code", "teacher_name", "email"}
    _validate(required.issubset(df.columns),
              f"teachers.xlsx missing columns: {required - set(df.columns)}")

    for col in ["teacher_code", "teacher_name", "email"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    teachers = {}
    for _, row in df.iterrows():
        _validate(row["teacher_code"] != "", f"teachers.xlsx row {_ + 2}: blank teacher_code")
        _validate(row["teacher_code"] not in teachers,
                  f"teachers.xlsx: duplicate teacher_code '{row['teacher_code']}'")

        teachers[row["teacher_code"]] = Teacher(
            teacher_code = row["teacher_code"],
            teacher_name = row["teacher_name"],
            email        = row["email"],
        )

    print(f"    → {len(teachers)} teachers loaded.")
    return teachers


def _load_teacher_subjects(path: str) -> dict[str, str]:
    """
    Loads teacher_subjects.xlsx
    Columns: teacher_code | subject_code
    Returns: {subject_code: teacher_code}
    Note: one teacher per subject (each class is taught by one person, not repeated)
    """
    print("  Loading teacher_subjects.xlsx ...")
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"teacher_code", "subject_code"}
    _validate(required.issubset(df.columns),
              f"teacher_subjects.xlsx missing columns: {required - set(df.columns)}")

    for col in ["teacher_code", "subject_code"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    teacher_subjects = {}
    for _, row in df.iterrows():
        _validate(row["teacher_code"] != "", f"teacher_subjects.xlsx row {_ + 2}: blank teacher_code")
        _validate(row["subject_code"] != "", f"teacher_subjects.xlsx row {_ + 2}: blank subject_code")

        if row["subject_code"] in teacher_subjects:
            _warn(f"subject '{row['subject_code']}' has multiple teachers assigned — "
                  f"keeping first ({teacher_subjects[row['subject_code']]}), ignoring {row['teacher_code']}")
            continue

        teacher_subjects[row["subject_code"]] = row["teacher_code"]

    print(f"    → {len(teacher_subjects)} teacher-subject mappings loaded.")
    return teacher_subjects


def _load_rooms(path: str) -> dict[str, Room]:
    """
    Loads rooms.xlsx
    Columns: room_id | room_name | capacity | room_type
    Returns: {room_id: Room}
    """
    print("  Loading rooms.xlsx ...")
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"room_id", "room_name", "capacity", "room_type"}
    _validate(required.issubset(df.columns),
              f"rooms.xlsx missing columns: {required - set(df.columns)}")

    for col in ["room_id", "room_name", "room_type"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce").fillna(0).astype(int)

    VALID_TYPES = {"lecture", "lab"}
    rooms = {}
    for _, row in df.iterrows():
        _validate(row["room_id"] != "", f"rooms.xlsx row {_ + 2}: blank room_id")
        _validate(row["room_id"] not in rooms,
                  f"rooms.xlsx: duplicate room_id '{row['room_id']}'")
        _validate(row["room_type"] in VALID_TYPES,
                  f"rooms.xlsx row {_ + 2}: invalid room_type='{row['room_type']}' "
                  f"(must be 'lecture' or 'lab')")

        rooms[row["room_id"]] = Room(
            room_id   = row["room_id"],
            room_name = row["room_name"],
            capacity  = row["capacity"],
            room_type = row["room_type"],
        )

    print(f"    → {len(rooms)} rooms loaded.")
    return rooms


# ─────────────────────────────────────────────────────────────────────────────
# Cross-file validation
# ─────────────────────────────────────────────────────────────────────────────

def _cross_validate(students, curriculum, subjects, teachers, teacher_subjects, rooms):
    print("\n  Running cross-file validation ...")
    errors = []

    # Every student's major/minor must appear as a program in curriculum
    all_programs = {prog for (prog, _) in curriculum.keys()}

    for enr, s in students.items():
        if s.semester <= 2:
            continue  # Foundation students have no major/minor yet
        if s.major and s.major not in all_programs:
            errors.append(f"Student {enr}: major '{s.major}' not found in curriculum.xlsx")
        if s.minor and s.minor not in all_programs:
            errors.append(f"Student {enr}: minor '{s.minor}' not found in curriculum.xlsx")

    # Every subject in teacher_subjects must exist in subjects
    for code, tcode in teacher_subjects.items():
        if code not in subjects:
            errors.append(f"teacher_subjects.xlsx: subject_code '{code}' not in curriculum.xlsx")
        if tcode not in teachers:
            errors.append(f"teacher_subjects.xlsx: teacher_code '{tcode}' not in teachers.xlsx")

    # Every subject in curriculum must have a teacher assigned
    for code in subjects:
        if code not in teacher_subjects:
            errors.append(f"Subject '{code}' ({subjects[code].subject_name}) has no teacher assigned in teacher_subjects.xlsx")

    if errors:
        print("\n  ✗ Cross-validation failed:")
        for e in errors:
            print(f"    - {e}")
        raise ValidationError(f"{len(errors)} cross-validation error(s) found. Fix the above before scheduling.")

    print("  ✓ All cross-file checks passed.")


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment groups builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_enrollment_groups(students, curriculum) -> dict[tuple, list[str]]:
    """
    Derives every real (semester, major, minor) combination from actual
    student data and maps each group to its list of subject_codes.

    How subjects are resolved per group:
      - major subjects: curriculum entries for (major, semester) where offered_as in {major, both}
      - minor subjects: curriculum entries for (minor, semester) where offered_as in {minor, both}
      - foundation:     curriculum entries for ("Foundation", semester)

    Returns: {(semester, major, minor): [subject_code, ...]}
    """
    print("\n  Building enrollment groups ...")

    # Collect unique (semester, major, minor) combos from real student data
    combos = set()
    for s in students.values():
        combos.add((s.semester, s.major, s.minor))

    enrollment_groups = {}

    for (semester, major, minor) in combos:
        subject_codes = []

        if semester <= 2 or major == "":
            # Foundation semester — all subjects from Foundation program
            foundation_entries = curriculum.get(("Foundation", semester), [])
            subject_codes = [e.subject_code for e in foundation_entries]
        else:
            # Major subjects
            major_entries = curriculum.get((major, semester), [])
            for e in major_entries:
                if e.offered_as in ("major", "both"):
                    subject_codes.append(e.subject_code)

            # Minor subjects (if student has a minor)
            if minor:
                minor_entries = curriculum.get((minor, semester), [])
                for e in minor_entries:
                    if e.offered_as in ("minor", "both"):
                        # Avoid double-adding if already in major list
                        if e.subject_code not in subject_codes:
                            subject_codes.append(e.subject_code)

        enrollment_groups[(semester, major, minor)] = subject_codes

    print(f"    → {len(enrollment_groups)} unique enrollment groups derived from student data.")
    for group, codes in sorted(enrollment_groups.items()):
        sem, maj, mn = group
        label = f"sem{sem} | {maj or 'Foundation'}" + (f" + {mn}" if mn else "")
        print(f"      {label:45s} → {len(codes)} subjects: {codes}")

    return enrollment_groups


# ─────────────────────────────────────────────────────────────────────────────
# Conflict graph builder  ← this is what the scheduler actually uses
# ─────────────────────────────────────────────────────────────────────────────

def _build_conflict_graph(enrollment_groups: dict) -> dict[str, set]:
    """
    Builds a conflict graph from enrollment groups.

    An edge exists between subject A and subject B if there is ANY enrollment
    group that contains both. This means they can never be scheduled at the
    same timeslot — a student would have to attend both simultaneously.

    Returns: {subject_code: set(subject_codes that conflict with it)}
    """
    print("\n  Building conflict graph ...")
    conflict_graph = defaultdict(set)

    for (semester, major, minor), subject_codes in enrollment_groups.items():
        # Every pair of subjects in this group conflicts with each other
        for i in range(len(subject_codes)):
            for j in range(i + 1, len(subject_codes)):
                a, b = subject_codes[i], subject_codes[j]
                conflict_graph[a].add(b)
                conflict_graph[b].add(a)

    total_edges = sum(len(v) for v in conflict_graph.values()) // 2
    print(f"    → {len(conflict_graph)} subjects in graph, {total_edges} conflict edges.")

    return dict(conflict_graph)


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def load_data(data_dir: str) -> dict:
    """
    Loads all 5 Excel files from data_dir, validates them, and returns
    a single dict containing all data structures needed by the scheduler.

    Args:
        data_dir: path to folder containing the 5 Excel files

    Returns:
        {
          "subjects"          : {subject_code: Subject},
          "teachers"          : {teacher_code: Teacher},
          "rooms"             : {room_id: Room},
          "students"          : {enrollment_no: Student},
          "curriculum"        : {(program, semester): [CurriculumEntry]},
          "teacher_subjects"  : {subject_code: teacher_code},
          "enrollment_groups" : {(semester, major, minor): [subject_code]},
          "conflict_graph"    : {subject_code: set(subject_code)},
        }
    """
    p = lambda f: os.path.join(data_dir, f)

    print("=" * 60)
    print("  DATA EXTRACTOR")
    print("=" * 60)

    # ── Load individual files ──
    students         = _load_students(p("students.xlsx"))
    curriculum, subjects = _load_curriculum(p("curriculum.xlsx"))
    teachers         = _load_teachers(p("teachers.xlsx"))
    teacher_subjects = _load_teacher_subjects(p("teacher_subjects.xlsx"))
    rooms            = _load_rooms(p("rooms.xlsx"))

    # ── Cross-file validation ──
    _cross_validate(students, curriculum, subjects, teachers, teacher_subjects, rooms)

    # ── Build derived structures ──
    enrollment_groups = _build_enrollment_groups(students, curriculum)
    conflict_graph    = _build_conflict_graph(enrollment_groups)

    print("\n" + "=" * 60)
    print("  EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"  Subjects          : {len(subjects)}")
    print(f"  Teachers          : {len(teachers)}")
    print(f"  Rooms             : {len(rooms)}")
    print(f"  Students          : {len(students)}")
    print(f"  Enrollment groups : {len(enrollment_groups)}")
    print(f"  Conflict edges    : {sum(len(v) for v in conflict_graph.values()) // 2}")
    print("=" * 60)

    return {
        "subjects"          : subjects,
        "teachers"          : teachers,
        "rooms"             : rooms,
        "students"          : students,
        "curriculum"        : curriculum,
        "teacher_subjects"  : teacher_subjects,
        "enrollment_groups" : enrollment_groups,
        "conflict_graph"    : conflict_graph,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Quick test when run directly
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = load_data("/home/claude/data")

    print("\n── Sample lookups ──")
    print("\nSubject TB2401:")
    print(" ", data["subjects"]["TB2401"])

    print("\nTeacher AP teaches:")
    taught = [code for code, t in data["teacher_subjects"].items() if t == "AP"]
    for code in taught:
        print(" ", data["subjects"][code])

    print("\nConflicts for TB2401 (subjects that can't share a slot with it):")
    for code in sorted(data["conflict_graph"].get("TB2401", [])):
        print(" ", data["subjects"].get(code, code))

    print("\nEnrollment group (sem=4, major=BBA, minor=Economics):")
    group = data["enrollment_groups"].get((4, "BBA", "Economics"), [])
    for code in group:
        print(" ", data["subjects"][code])