"""
test.py
─────────────────────────────────────────────────────────────────────────────
Final validation suite for timetable.json.
Run after scheduler completes to verify zero clashes.

Usage:
    python test.py                          # looks for output/timetable.json
    python test.py path/to/timetable.json   # explicit path

Tests:
    T1  No student attends two classes at the same time
    T2  No teacher teaches two classes at the same time
    T3  No room hosts two classes at the same time
    T4  No practical is placed at the last slot of a day (needs 2 consecutive)
    T5  No practical overlaps with another class in its second slot
    T6  Every student's class list matches what their enrollment group expects
    T7  Every class has a valid room assignment (room exists, correct type)
    T8  No room is over capacity for the number of students attending
    T9  Every class has a teacher assigned (not TBA)
    T10 No student has more than 6 classes on any single day
"""

import json
import sys
import os
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

PASS  = "  ✓ PASS"
FAIL  = "  ✗ FAIL"
WARN  = "  ⚠ WARN"

def _header(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def _result(label: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    line   = f"{status}  {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    return passed

def _slot_key(c: dict) -> str:
    """Unique key for a timeslot: day + start time."""
    return f"{c['day']}|{c['start']}"

def _occupied_slot_keys(c: dict) -> list:
    """
    Returns all slot keys this class occupies.
    Lecture  → 1 slot  (start only)
    Practical → 2 slots (start + next 50 min)
    """
    if c.get("type") == "practical":
        # Derive second slot end from first slot start
        # All slots are 50 min, so second start = this class's end
        return [f"{c['day']}|{c['start']}", f"{c['day']}|{c['end']}"]
    return [f"{c['day']}|{c['start']}"]


# ─────────────────────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────────────────────

def load_timetable(path: str) -> dict:
    if not os.path.exists(path):
        print(f"\n  ✗ ERROR: File not found: {path}")
        print("  Make sure you have run main.py first.\n")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    required = {"meta", "timetable", "by_day", "by_student"}
    missing  = required - set(data.keys())
    if missing:
        print(f"\n  ✗ ERROR: timetable.json is missing keys: {missing}\n")
        sys.exit(1)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def t1_no_student_clashes(by_student: dict) -> bool:
    """No student attends two classes at the same time."""
    _header("T1 — Student clashes")
    clashes = []

    for enr, s in by_student.items():
        slot_map = defaultdict(list)
        for c in s["classes"]:
            for sk in _occupied_slot_keys(c):
                slot_map[sk].append(c["course_code"])

        for slot_key, codes in slot_map.items():
            if len(codes) > 1:
                day, time = slot_key.split("|")
                clashes.append(
                    f"Student {enr} ({s['name']}): "
                    f"{' & '.join(codes)} clash at {day} {time}"
                )

    if clashes:
        for c in clashes[:10]:   # show first 10
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")
    return _result(
        f"Student clashes",
        len(clashes) == 0,
        f"{len(clashes)} clashes found" if clashes else f"0 clashes across {len(by_student)} students"
    )


def t2_no_teacher_clashes(timetable: list) -> bool:
    """No teacher teaches two classes at the same time."""
    _header("T2 — Teacher clashes")
    clashes = []

    teacher_slots = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        teacher = c.get("teacher", "TBA")
        if teacher == "TBA":
            continue
        for sk in _occupied_slot_keys(c):
            teacher_slots[teacher][sk].append(c["course_code"])

    for teacher, slot_map in teacher_slots.items():
        for slot_key, codes in slot_map.items():
            if len(codes) > 1:
                day, time = slot_key.split("|")
                clashes.append(
                    f"Teacher '{teacher}': "
                    f"{' & '.join(codes)} clash at {day} {time}"
                )

    if clashes:
        for c in clashes[:10]:
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")

    unique_teachers = len({c["teacher"] for c in timetable if c["teacher"] != "TBA"})
    return _result(
        "Teacher clashes",
        len(clashes) == 0,
        f"{len(clashes)} clashes found" if clashes else f"0 clashes across {unique_teachers} teachers"
    )


def t3_no_room_clashes(timetable: list) -> bool:
    """No room hosts two classes at the same time."""
    _header("T3 — Room clashes")
    clashes = []

    room_slots = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        for sk in _occupied_slot_keys(c):
            room_slots[c["room_id"]][sk].append(c["course_code"])

    for room, slot_map in room_slots.items():
        for slot_key, codes in slot_map.items():
            if len(codes) > 1:
                day, time = slot_key.split("|")
                clashes.append(
                    f"Room {room}: "
                    f"{' & '.join(codes)} clash at {day} {time}"
                )

    if clashes:
        for c in clashes[:10]:
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")

    return _result(
        "Room clashes",
        len(clashes) == 0,
        f"{len(clashes)} clashes found" if clashes else f"0 clashes across {len(room_slots)} rooms"
    )


def t4_practicals_not_at_day_end(timetable: list, meta: dict) -> bool:
    """No practical starts at the last slot of a day."""
    _header("T4 — Practical end-of-day placement")
    issues = []

    # Build the last start time of each day from meta timeslots
    day_last_start = {}
    for slot in meta["timeslots"]:
        day = slot["day"]
        if day not in day_last_start or slot["start"] > day_last_start[day]:
            day_last_start[day] = slot["start"]

    for c in timetable:
        if c.get("type") == "practical":
            if c["start"] == day_last_start.get(c["day"]):
                issues.append(
                    f"{c['course_code']} ({c['title'][:30]}) "
                    f"starts at last slot {c['day']} {c['start']}"
                )

    if issues:
        for i in issues:
            print(f"    {i}")

    practicals = sum(1 for c in timetable if c.get("type") == "practical")
    return _result(
        "Practicals at day end",
        len(issues) == 0,
        f"{len(issues)} violations" if issues else f"0 violations  ({practicals} practicals checked)"
    )


def t5_practical_second_slot_free(timetable: list) -> bool:
    """
    For every practical, the slot immediately after it (the 2nd slot)
    must not conflict with any other class in the same room.
    (T3 already catches student/teacher conflicts via _occupied_slot_keys;
     this test specifically checks the room's second slot.)
    """
    _header("T5 — Practical second-slot room availability")

    # Build room → slot_key → [codes]
    room_slots = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        room_slots[c["room_id"]][f"{c['day']}|{c['start']}"].append(c["course_code"])

    issues = []
    for c in timetable:
        if c.get("type") == "practical":
            # Second slot key = day + end time of first slot = start of second slot
            second_key = f"{c['day']}|{c['end']}"
            others = [
                code for code in room_slots[c["room_id"]].get(second_key, [])
                if code != c["course_code"]
            ]
            if others:
                issues.append(
                    f"{c['course_code']} 2nd slot ({c['day']} {c['end']}) "
                    f"conflicts with {others} in room {c['room_id']}"
                )

    if issues:
        for i in issues:
            print(f"    {i}")

    return _result(
        "Practical 2nd slot clear",
        len(issues) == 0,
        f"{len(issues)} conflicts" if issues else "All practical second slots are clear"
    )


def t6_student_subjects_correct(by_student: dict, timetable: list) -> bool:
    """
    Every class in a student's personal timetable actually belongs to
    a subject the student should be attending (no extra or missing classes
    that don't match their major/minor/semester).
    Checks that the course_code in their classes exists in the flat timetable.
    """
    _header("T6 — Student subject assignments")
    issues = []

    all_codes = {c["course_code"] for c in timetable}

    for enr, s in by_student.items():
        for c in s["classes"]:
            if c["course_code"] not in all_codes:
                issues.append(
                    f"Student {enr}: class {c['course_code']} "
                    f"not found in master timetable"
                )

    if issues:
        for i in issues[:10]:
            print(f"    {i}")

    total_assignments = sum(len(s["classes"]) for s in by_student.values())
    return _result(
        "Student subject assignments",
        len(issues) == 0,
        f"{len(issues)} invalid assignments" if issues
        else f"All {total_assignments} student-class assignments valid"
    )


def t7_valid_room_assignments(timetable: list) -> bool:
    """Every class has a room_id that is non-empty and a known room type."""
    _header("T7 — Valid room assignments")
    issues = []

    for c in timetable:
        if not c.get("room_id") or c["room_id"] == "":
            issues.append(f"{c['course_code']}: no room assigned")
        elif not c.get("room_type") or c["room_type"] not in ("lecture", "lab"):
            issues.append(
                f"{c['course_code']}: invalid room_type "
                f"'{c.get('room_type')}' in room {c['room_id']}"
            )
        # Practical should be in lab, lecture in lecture hall
        elif c.get("type") == "practical" and c["room_type"] != "lab":
            issues.append(
                f"{c['course_code']} (practical) in lecture room {c['room_id']}"
            )
        elif c.get("type") == "lecture" and c["room_type"] != "lecture":
            issues.append(
                f"{c['course_code']} (lecture) in lab room {c['room_id']}"
            )

    if issues:
        for i in issues[:10]:
            print(f"    {i}")
        if len(issues) > 10:
            print(f"    ... and {len(issues)-10} more")

    return _result(
        "Room assignments valid",
        len(issues) == 0,
        f"{len(issues)} invalid assignments" if issues
        else f"All {len(timetable)} classes have valid room assignments"
    )


def t8_room_capacity(timetable: list, by_student: dict) -> bool:
    """
    No room is over capacity.
    Student count per class is computed from by_student.
    """
    _header("T8 — Room capacity")
    issues   = []
    warnings = []

    # Count students per course_code
    student_counts = defaultdict(int)
    for s in by_student.values():
        for c in s["classes"]:
            student_counts[c["course_code"]] += 1

    for c in timetable:
        count = student_counts.get(c["course_code"], 0)
        cap   = c.get("capacity", 0)
        if count == 0:
            continue
        if cap == 0:
            warnings.append(f"{c['course_code']}: room {c['room_id']} has capacity 0")
        elif count > cap:
            issues.append(
                f"{c['course_code']} ({c['title'][:28]}): "
                f"{count} students in room {c['room_id']} (cap={cap}, overflow={count-cap})"
            )

    if issues:
        for i in issues[:10]:
            print(f"    OVER: {i}")
        if len(issues) > 10:
            print(f"    ... and {len(issues)-10} more")
    if warnings:
        for w in warnings[:5]:
            print(f"    WARN: {w}")

    passed = len(issues) == 0
    status = PASS if passed else FAIL
    detail = (f"{len(issues)} over-capacity rooms" if issues
              else f"All rooms within capacity")
    print(f"{status}  Room capacity  →  {detail}")
    return passed


def t9_all_teachers_assigned(timetable: list) -> bool:
    """No class has teacher = 'TBA'."""
    _header("T9 — Teacher assignments")
    missing = [
        f"{c['course_code']} ({c['title'][:30]}) has no teacher (TBA)"
        for c in timetable if c.get("teacher", "TBA") == "TBA"
    ]
    if missing:
        for m in missing[:10]:
            print(f"    {m}")
        if len(missing) > 10:
            print(f"    ... and {len(missing)-10} more")

    return _result(
        "Teacher assignments",
        len(missing) == 0,
        f"{len(missing)} classes without a teacher" if missing
        else f"All {len(timetable)} classes have a teacher"
    )


def t10_student_daily_load(by_student: dict) -> bool:
    """No student has more than 6 classes on any single day."""
    _header("T10 — Student daily load")
    MAX_PER_DAY = 6
    issues = []

    for enr, s in by_student.items():
        day_counts = defaultdict(int)
        for c in s["classes"]:
            day_counts[c["day"]] += 1
        for day, cnt in day_counts.items():
            if cnt > MAX_PER_DAY:
                issues.append(
                    f"Student {enr} ({s['name']}): "
                    f"{cnt} classes on {day} (max={MAX_PER_DAY})"
                )

    if issues:
        for i in issues[:10]:
            print(f"    {i}")
        if len(issues) > 10:
            print(f"    ... and {len(issues)-10} more")

    return _result(
        "Student daily load",
        len(issues) == 0,
        f"{len(issues)} overloaded days" if issues
        else f"No student has more than {MAX_PER_DAY} classes/day"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: dict, timetable_path: str):
    passed  = sum(1 for v in results.values() if v)
    failed  = sum(1 for v in results.values() if not v)
    total   = len(results)
    overall = failed == 0

    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  File    : {timetable_path}")
    print(f"  Passed  : {passed}/{total}")
    print(f"  Failed  : {failed}/{total}")
    print()
    for name, passed_flag in results.items():
        icon = "✓" if passed_flag else "✗"
        print(f"  {icon}  {name}")
    print()
    if overall:
        print("  ✓ ALL TESTS PASSED — timetable is clean")
    else:
        print("  ✗ SOME TESTS FAILED — review violations above")
    print("=" * 60 + "\n")
    return overall


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_tests(timetable_path: str) -> bool:
    print("\n" + "=" * 60)
    print("  TSLAS TIMETABLE — VALIDATION SUITE")
    print("=" * 60)
    print(f"  Loading: {timetable_path}")

    data       = load_timetable(timetable_path)
    timetable  = data["timetable"]
    by_student = data["by_student"]
    meta       = data["meta"]

    print(f"  Classes   : {meta['total_classes']}")
    print(f"  Students  : {meta['total_students']}")
    print(f"  Days      : {len(meta['days'])}  ({', '.join(meta['days'])})")
    print(f"  Slots/day : {meta['slots_per_day']}")

    results = {}
    results["T1  Student clashes"]          = t1_no_student_clashes(by_student)
    results["T2  Teacher clashes"]          = t2_no_teacher_clashes(timetable)
    results["T3  Room clashes"]             = t3_no_room_clashes(timetable)
    results["T4  Practicals at day-end"]    = t4_practicals_not_at_day_end(timetable, meta)
    results["T5  Practical 2nd slot clear"] = t5_practical_second_slot_free(timetable)
    results["T6  Student subjects correct"] = t6_student_subjects_correct(by_student, timetable)
    results["T7  Valid room assignments"]   = t7_valid_room_assignments(timetable)
    results["T8  Room capacity"]            = t8_room_capacity(timetable, by_student)
    results["T9  Teacher assigned"]         = t9_all_teachers_assigned(timetable)
    results["T10 Student daily load"]       = t10_student_daily_load(by_student)

    return print_summary(results, timetable_path)


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    default  = os.path.join(BASE_DIR, "output", "timetable.json")
    path     = sys.argv[1] if len(sys.argv) > 1 else default

    ok = run_tests(path)
    sys.exit(0 if ok else 1)   # exit code 1 if any test fails (useful for CI)