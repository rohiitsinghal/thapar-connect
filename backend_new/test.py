"""
test.py  v3
─────────────────────────────────────────────────────────────────────────────
Final validation suite for timetable.json (unit-based scheduler).

Usage:
    python test.py                          # looks for output/timetable.json
    python test.py path/to/timetable.json   # explicit path

Tests:
    T1  No student attends two classes at the same time
    T2  No teacher teaches two classes at the same time
    T3  No room hosts two classes at the same time
    T4  No practical starts at the last slot of a day
    T5  No practical's second slot is occupied by another class in the same room
    T6  Every class in a student's list exists in the master timetable
    T7  Every class has a valid room assignment and correct room type
    T8  No room is over capacity for the students attending
    T9  Every class has a teacher assigned (not TBA)
    T10 No student has more than 8 class sessions in a single day
    T11 No unit_id is scheduled more than once (internal consistency check)

Exit code 0 = all pass, 1 = at least one failure (CI-friendly).
"""

import json
import sys
import os
from collections import defaultdict

PASS = "  ✓ PASS"
FAIL = "  ✗ FAIL"


def _header(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _result(label, passed, detail=""):
    status = PASS if passed else FAIL
    line   = f"{status}  {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    return passed


def _occupied_slot_keys(c):
    """
    Returns all slot_index values this class occupies, as integers.

    IMPORTANT: we use the integer slot_index, NOT a day+time string.
    A practical spanning slot 5 and slot 6 occupies slot_index 5 and 6.
    Using clock-time strings instead (e.g. day+end_time) is WRONG because
    a class starting exactly when a practical's second slot ends would
    share the same time-string key as that second slot, producing a false
    clash even though they are different, non-overlapping slot_index values.
    """
    start_idx = c["slot_index"]
    if c.get("type") == "practical":
        return [start_idx, start_idx + 1]
    return [start_idx]


def _uid(c):
    """Get the unique identifier for a class entry — unit_id if present,
    falls back to course_code for older timetable.json formats."""
    return c.get("unit_id", c["course_code"])


# ─────────────────────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────────────────────

def load_timetable(path):
    if not os.path.exists(path):
        print(f"\n  ✗ ERROR: File not found: {path}")
        print("  Run main.py first to generate the timetable.\n")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    required = {"meta", "timetable", "by_day", "by_student"}
    missing  = required - set(data.keys())
    if missing:
        print(f"\n  ✗ ERROR: timetable.json missing keys: {missing}\n")
        sys.exit(1)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Student clashes
# ─────────────────────────────────────────────────────────────────────────────

def t1_no_student_clashes(by_student):
    _header("T1 — Student clashes")
    clashes = []

    for enr, s in by_student.items():
        slot_map = defaultdict(list)
        for c in s["classes"]:
            for sk in _occupied_slot_keys(c):
                slot_map[sk].append(_uid(c))
        for slot_key, ids in slot_map.items():
            if len(ids) > 1:
                clashes.append(
                    f"Student {enr} ({s['name']}): "
                    f"{' & '.join(ids)} clash at slot_index {slot_key}"
                )

    if clashes:
        for c in clashes[:10]:
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")

    return _result(
        "Student clashes", len(clashes) == 0,
        f"{len(clashes)} clashes" if clashes
        else f"0 clashes across {len(by_student)} students"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Teacher clashes
# ─────────────────────────────────────────────────────────────────────────────

def t2_no_teacher_clashes(timetable):
    _header("T2 — Teacher clashes")
    clashes = []

    teacher_slots = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        teacher = c.get("teacher", "TBA")
        if teacher == "TBA":
            continue
        for sk in _occupied_slot_keys(c):
            teacher_slots[teacher][sk].append(_uid(c))

    for teacher, slot_map in teacher_slots.items():
        for slot_key, ids in slot_map.items():
            if len(ids) > 1:
                clashes.append(
                    f"Teacher '{teacher}': "
                    f"{' & '.join(ids)} clash at slot_index {slot_key}"
                )

    if clashes:
        for c in clashes[:10]:
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")

    unique_teachers = len({c["teacher"] for c in timetable
                           if c.get("teacher") != "TBA"})
    return _result(
        "Teacher clashes", len(clashes) == 0,
        f"{len(clashes)} clashes" if clashes
        else f"0 clashes across {unique_teachers} teachers"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Room clashes
# ─────────────────────────────────────────────────────────────────────────────

def t3_no_room_clashes(timetable):
    _header("T3 — Room clashes")
    clashes = []

    room_slots = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        for sk in _occupied_slot_keys(c):
            room_slots[c["room_id"]][sk].append(_uid(c))

    for room, slot_map in room_slots.items():
        for slot_key, ids in slot_map.items():
            if len(ids) > 1:
                clashes.append(
                    f"Room {room}: "
                    f"{' & '.join(ids)} clash at slot_index {slot_key}"
                )

    if clashes:
        for c in clashes[:10]:
            print(f"    {c}")
        if len(clashes) > 10:
            print(f"    ... and {len(clashes)-10} more")

    return _result(
        "Room clashes", len(clashes) == 0,
        f"{len(clashes)} clashes" if clashes
        else f"0 clashes across {len(room_slots)} rooms"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Practicals not at last slot of day
# ─────────────────────────────────────────────────────────────────────────────

def t4_practicals_not_at_day_end(timetable, meta):
    _header("T4 — Practical end-of-day placement")

    day_last_start = {}
    for slot in meta["timeslots"]:
        day = slot["day"]
        if day not in day_last_start or slot["start"] > day_last_start[day]:
            day_last_start[day] = slot["start"]

    issues = []
    for c in timetable:
        if c.get("type") == "practical":
            if c["start"] == day_last_start.get(c["day"]):
                issues.append(
                    f"{_uid(c)} starts at last slot {c['day']} {c['start']}"
                )

    if issues:
        for i in issues:
            print(f"    {i}")

    practicals = sum(1 for c in timetable if c.get("type") == "practical")
    return _result(
        "Practicals at day end", len(issues) == 0,
        f"{len(issues)} violations" if issues
        else f"0 violations  ({practicals} practicals checked)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Practical second slot room free
# ─────────────────────────────────────────────────────────────────────────────

def t5_practical_second_slot_free(timetable):
    """
    Checks that no other class occupies a practical's SECOND slot_index
    in the same room. Uses slot_index (integer) for the check, not
    day+time strings, to avoid false positives when another class
    legitimately starts at the same clock time the practical ends.
    """
    _header("T5 — Practical second-slot room availability")

    # room_id -> slot_index -> [unit_ids occupying that exact slot_index]
    room_slot_index = defaultdict(lambda: defaultdict(list))
    for c in timetable:
        for slot_idx in _occupied_slot_keys(c):
            room_slot_index[c["room_id"]][slot_idx].append(_uid(c))

    issues = []
    for c in timetable:
        if c.get("type") == "practical":
            second_slot_idx = c["slot_index"] + 1
            others = [
                uid for uid in room_slot_index[c["room_id"]].get(second_slot_idx, [])
                if uid != _uid(c)
            ]
            if others:
                issues.append(
                    f"{_uid(c)} 2nd slot (slot_index {second_slot_idx}, "
                    f"{c['day']} after {c['start']}) conflicts with {others} "
                    f"in room {c['room_id']}"
                )

    if issues:
        for i in issues:
            print(f"    {i}")

    return _result(
        "Practical 2nd slot clear", len(issues) == 0,
        f"{len(issues)} conflicts" if issues
        else "All practical second slots are clear"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T6 — Student class list integrity
# ─────────────────────────────────────────────────────────────────────────────

def t6_student_subjects_correct(by_student, timetable):
    _header("T6 — Student class list integrity")

    all_ids = {_uid(c) for c in timetable}
    issues  = []

    for enr, s in by_student.items():
        for c in s["classes"]:
            uid = _uid(c)
            if uid not in all_ids:
                issues.append(f"Student {enr}: '{uid}' not in master timetable")

    if issues:
        for i in issues[:10]:
            print(f"    {i}")

    total = sum(len(s["classes"]) for s in by_student.values())
    return _result(
        "Student class list integrity", len(issues) == 0,
        f"{len(issues)} invalid entries" if issues
        else f"All {total} student-class assignments valid"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T7 — Valid room assignments and correct room type
# ─────────────────────────────────────────────────────────────────────────────

def t7_valid_room_assignments(timetable):
    _header("T7 — Valid room assignments")
    issues = []

    for c in timetable:
        uid = _uid(c)
        if not c.get("room_id"):
            issues.append(f"{uid}: no room assigned")
        elif c.get("room_type") not in ("lecture", "lab"):
            issues.append(f"{uid}: invalid room_type '{c.get('room_type')}'")
        elif c.get("type") == "practical" and c["room_type"] != "lab":
            issues.append(f"{uid} (practical) in lecture room {c['room_id']}")
        elif c.get("type") in ("lecture", "tutorial") and c["room_type"] != "lecture":
            issues.append(f"{uid} ({c['type']}) in lab room {c['room_id']}")

    if issues:
        for i in issues[:10]:
            print(f"    {i}")
        if len(issues) > 10:
            print(f"    ... and {len(issues)-10} more")

    return _result(
        "Room assignments valid", len(issues) == 0,
        f"{len(issues)} invalid" if issues
        else f"All {len(timetable)} units have valid room assignments"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T8 — Room capacity
# ─────────────────────────────────────────────────────────────────────────────

def t8_room_capacity(timetable, by_student):
    _header("T8 — Room capacity")

    student_counts = defaultdict(int)
    for s in by_student.values():
        for c in s["classes"]:
            student_counts[_uid(c)] += 1

    issues   = []
    warnings = []

    for c in timetable:
        uid   = _uid(c)
        count = student_counts.get(uid, 0)
        cap   = c.get("capacity", 0)
        if count == 0:
            continue
        if cap == 0:
            warnings.append(f"{uid}: room {c['room_id']} has capacity 0")
        elif count > cap:
            issues.append(
                f"{uid} ({c.get('title', '')[:28]}): "
                f"{count} students in {c['room_id']} "
                f"(cap={cap}, overflow={count-cap})"
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
    return _result(
        "Room capacity", passed,
        f"{len(issues)} over-capacity rooms" if issues
        else "All rooms within capacity"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T9 — All teachers assigned
# ─────────────────────────────────────────────────────────────────────────────

def t9_all_teachers_assigned(timetable):
    _header("T9 — Teacher assignments")

    missing = [
        f"{_uid(c)} ({c.get('title','')[:30]}) — TBA"
        for c in timetable if c.get("teacher", "TBA") == "TBA"
    ]

    if missing:
        for m in missing[:10]:
            print(f"    {m}")
        if len(missing) > 10:
            print(f"    ... and {len(missing)-10} more")

    return _result(
        "Teacher assignments", len(missing) == 0,
        f"{len(missing)} units without teacher" if missing
        else f"All {len(timetable)} units have a teacher"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T10 — Student daily load
# ─────────────────────────────────────────────────────────────────────────────

def t10_student_daily_load(by_student, max_per_day=8):
    _header(f"T10 — Student daily load (max {max_per_day} sessions/day)")
    issues = []

    for enr, s in by_student.items():
        day_counts = defaultdict(int)
        for c in s["classes"]:
            day_counts[c["day"]] += 1
        for day, cnt in day_counts.items():
            if cnt > max_per_day:
                issues.append(
                    f"Student {enr} ({s['name']}): {cnt} sessions on {day}"
                )

    if issues:
        for i in issues[:10]:
            print(f"    {i}")
        if len(issues) > 10:
            print(f"    ... and {len(issues)-10} more")

    return _result(
        "Student daily load", len(issues) == 0,
        f"{len(issues)} overloaded days" if issues
        else f"No student exceeds {max_per_day} sessions/day"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T11 — No unit_id scheduled more than once
# ─────────────────────────────────────────────────────────────────────────────

def t11_no_duplicate_units(timetable):
    _header("T11 — Duplicate unit check")

    seen = {}
    duplicates = []
    for c in timetable:
        uid = c.get("unit_id")
        if uid is None:
            continue
        if uid in seen:
            duplicates.append(
                f"'{uid}' appears twice: "
                f"{seen[uid]['day']} {seen[uid]['start']}  AND  "
                f"{c['day']} {c['start']}"
            )
        seen[uid] = c

    if duplicates:
        for d in duplicates[:10]:
            print(f"    {d}")

    return _result(
        "No duplicate unit_ids", len(duplicates) == 0,
        f"{len(duplicates)} duplicates" if duplicates
        else f"All {len(seen)} unit_ids scheduled exactly once"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results, path):
    passed  = sum(1 for v in results.values() if v)
    failed  = sum(1 for v in results.values() if not v)
    total   = len(results)
    overall = failed == 0

    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  File    : {path}")
    print(f"  Passed  : {passed}/{total}")
    print(f"  Failed  : {failed}/{total}")
    print()
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'}  {name}")
    print()
    if overall:
        print("  ✓ ALL TESTS PASSED — timetable is clean")
    else:
        print("  ✗ SOME TESTS FAILED — review violations above.")
        print("    If T1/T2/T3/T5 failed: the SA likely did not finish —")
        print("    re-run main.py and let it reach 'All hard constraints satisfied'")
        print("    before generating the timetable used for testing.")
    print("=" * 60 + "\n")
    return overall


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_tests(path):
    print("\n" + "=" * 60)
    print("  TSLAS TIMETABLE — VALIDATION SUITE  v3")
    print("=" * 60)
    print(f"  Loading: {path}")

    data       = load_timetable(path)
    timetable  = data["timetable"]
    by_student = data["by_student"]
    meta       = data["meta"]

    lec  = sum(1 for c in timetable if c.get("type") == "lecture")
    tut  = sum(1 for c in timetable if c.get("type") == "tutorial")
    prac = sum(1 for c in timetable if c.get("type") == "practical")

    print(f"  Total sessions : {meta['total_classes']}  "
          f"({lec} lectures + {tut} tutorials + {prac} practicals)")
    print(f"  Students       : {meta['total_students']}")
    print(f"  Days           : {', '.join(meta['days'])}")
    print(f"  Slots/day      : {meta['slots_per_day']}  "
          f"({meta.get('slot_duration_minutes', 50)} min each)")

    results = {}
    results["T1  Student clashes"]          = t1_no_student_clashes(by_student)
    results["T2  Teacher clashes"]          = t2_no_teacher_clashes(timetable)
    results["T3  Room clashes"]             = t3_no_room_clashes(timetable)
    results["T4  Practicals at day-end"]    = t4_practicals_not_at_day_end(timetable, meta)
    results["T5  Practical 2nd slot clear"] = t5_practical_second_slot_free(timetable)
    results["T6  Student list integrity"]   = t6_student_subjects_correct(by_student, timetable)
    results["T7  Valid room assignments"]   = t7_valid_room_assignments(timetable)
    results["T8  Room capacity"]            = t8_room_capacity(timetable, by_student)
    results["T9  Teacher assigned"]         = t9_all_teachers_assigned(timetable)
    results["T10 Student daily load"]       = t10_student_daily_load(by_student)
    results["T11 No duplicate units"]       = t11_no_duplicate_units(timetable)

    return print_summary(results, path)


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    default  = os.path.join(BASE_DIR, "output", "timetable.json")
    path     = sys.argv[1] if len(sys.argv) > 1 else default

    ok = run_tests(path)
    sys.exit(0 if ok else 1)