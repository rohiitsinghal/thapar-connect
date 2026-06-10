"""
extractor.py
Place this in: backend_new/
Excel files go in: backend_new/data/
  - backend_new/data/software_files.xlsx
  - backend_new/data/rooms.xlsx
"""

import openpyxl
import json
import os
from collections import defaultdict
from dataclasses import dataclass, asdict

# ─────────────────────────────────────────────────────────────────────────────
# Canonical program name map
# ─────────────────────────────────────────────────────────────────────────────
PROGRAM_NAME_MAP = {
    "data science & ai":               "Data Science & AI",
    "data science and ai":             "Data Science & AI",
    "data science":                    "Data Science & AI",
    "cs/dsai":                         "Data Science & AI",
    "computer science":                "Computer Science",
    "computer sciences":               "Computer Science",
    "psychology":                      "Psychology",
    "b.a psychology":                  "Psychology",
    "b.a psychology hons.":            "Psychology",
    "psychology/cognitive science":    "Psychology",
    "political science":               "Political Science",
    "political science,":              "Political Science",
    "philosophy/political science":    "Political Science",
    "political science/economics":     "Political Science",
    "environment & sustainability":    "Environment & Sustainability",
    "environment and sustainability":  "Environment & Sustainability",
    "philosophy":                      "Philosophy",
    "casp":                            "CASP",
    "casp ":                           "CASP",
    "casp (art & media)":              "CASP",
    "arts & media":                    "CASP",
    "arts & media   ":                 "CASP",
    "lcs":                             "LCS",
    "literary and cultural studies":   "LCS",
    "sociology":                       "Sociology",
    "sociology ":                      "Sociology",
    "bba":                             "BBA",
    "economics":                       "Economics",
    "history":                         "History",
    "mathematics":                     "Mathematics",
    "physics":                         "Physics",
    "biotechnology":                   "Biotechnology",
    "cognitive science":               "Cognitive Science",
    "b com":                           "B Com",
    "chemistry":                       "Chemistry",
    "chemsitry":                       "Chemistry",
}

VALID_OFFERED_AS = {"major", "minor", "both", "major/minor"}


def _canonical(name: str) -> str:
    if not name or str(name).strip() in ("", "nan", "None"):
        return ""
    key = str(name).strip().lower()
    if key not in PROGRAM_NAME_MAP:
        print(f"    ⚠  Unknown program '{name}' — keeping as-is. Add to PROGRAM_NAME_MAP.")
        return str(name).strip()
    return PROGRAM_NAME_MAP[key]


def _norm_offered(val) -> str:
    if not val or str(val).strip() in ("", "nan", "None"):
        return ""
    n = str(val).strip().lower()
    if n == "both":
        n = "major/minor"
    return n


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Subject:
    course_code: str
    title:       str
    L: int
    T: int
    P: int
    credits: int

@dataclass
class Teacher:
    teacher_code: str
    teacher_name: str
    courses:      list

@dataclass
class Room:
    room_id:   str
    capacity:  int
    room_type: str   # "lecture" | "lab"

@dataclass
class Student:
    enrollment_no: str
    name:     str
    email:    str
    major:    str
    minor:    str
    semester: int

@dataclass
class CurriculumEntry:
    program:      str
    semester:     int
    course_code:  str
    title:        str
    credits:      int
    offered_as:   str
    teacher:      str
    teacher_code: str


# ─────────────────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_curriculum_and_teachers(wb):
    """
    Reads 'curriculum', 'teachers', 'teacher_ name' sheets from software_files.xlsx
    Row 0 of curriculum = title banner (skip)
    Row 1 of curriculum = actual headers
    """
    print("\n  [1/3] Loading curriculum + teachers from software_files.xlsx ...")

    # ── curriculum sheet ──
    ws        = wb['curriculum']
    rows      = list(ws.iter_rows(values_only=True))
    data_rows = [r for r in rows[2:] if any(c is not None for c in r)]

    curriculum       = defaultdict(list)
    subjects         = {}
    teacher_subjects = {}           # {course_code: teacher_name}
    teacher_courses  = defaultdict(set)
    teacher_info     = {}           # {teacher_code: teacher_name}

    for r in data_rows:
        program = _canonical(str(r[1]).strip() if r[1] else "")

        # Fix corrupt semester (Excel stores datetime for some cells)
        raw_sem = r[2]
        if hasattr(raw_sem, 'day'):
            semester = raw_sem.day
        else:
            try:
                semester = int(float(str(raw_sem)))
            except Exception:
                print(f"    ⚠  Cannot parse semester '{raw_sem}' — skipping row")
                continue

        code         = str(r[3]).strip() if r[3] else ""
        title        = str(r[4]).strip() if r[4] else ""
        L            = int(r[5] or 0)
        T            = int(r[6] or 0)
        P            = int(r[7] or 0)
        credits      = int(r[8] or 0)
        offered_raw  = str(r[9]).strip() if r[9] else ""
        teacher_name = str(r[10]).strip() if r[10] else ""
        teacher_code = str(r[11]).strip() if r[11] else ""

        if not program or not code:
            continue

        offered = _norm_offered(offered_raw)
        if offered not in VALID_OFFERED_AS:
            print(f"    ⚠  Invalid offered_as='{offered_raw}' for {code} — skipping")
            continue

        entry = CurriculumEntry(
            program=program, semester=semester, course_code=code,
            title=title, credits=credits, offered_as=offered,
            teacher=teacher_name, teacher_code=teacher_code,
        )
        curriculum[(program, semester)].append(entry)

        if code not in subjects:
            subjects[code] = Subject(course_code=code, title=title,
                                     L=L, T=T, P=P, credits=credits)

        if teacher_name and teacher_code:
            teacher_subjects[code] = teacher_name
            teacher_info[teacher_code] = teacher_name
            teacher_courses[teacher_code].add(code)

    # ── teacher_ name sheet (canonical teacher roster — highest priority) ──
    ws_tn = wb['teacher_ name']
    for r in list(ws_tn.iter_rows(values_only=True))[1:]:
        if not any(c for c in r):
            continue
        code = str(r[0]).strip() if r[0] else ""
        name = str(r[1]).strip() if r[1] else ""
        tc   = str(r[2]).strip() if r[2] else ""
        if not code or not name:
            continue
        teacher_subjects[code] = name      # overrides curriculum inline value
        if tc:
            teacher_info[tc] = name
            teacher_courses[tc].add(code)

    # ── teachers sheet (subject_code | teacher_name | teacher_code) ──
    ws_t = wb['teachers']
    for r in list(ws_t.iter_rows(values_only=True))[1:]:
        if not any(c for c in r):
            continue
        code = str(r[0]).strip() if r[0] else ""
        name = str(r[1]).strip() if r[1] else ""
        tc   = str(r[2]).strip() if r[2] else ""
        if not code or not name or code == "nan" or name == "nan":
            continue
        if code not in teacher_subjects:   # only fill gaps
            teacher_subjects[code] = name
        if tc and tc not in ("nan", ""):
            teacher_info[tc] = name
            teacher_courses[tc].add(code)

    # Build Teacher objects
    teachers = {
        tc: Teacher(teacher_code=tc, teacher_name=name,
                    courses=sorted(teacher_courses[tc]))
        for tc, name in teacher_info.items()
    }

    curriculum = dict(curriculum)
    print(f"    ✓ {len(subjects)} subjects | "
          f"{sum(len(v) for v in curriculum.values())} curriculum entries | "
          f"{len(curriculum)} (program, semester) combinations")
    print(f"    ✓ {len(teachers)} teachers | {len(teacher_subjects)} subject→teacher mappings")
    return curriculum, subjects, teachers, teacher_subjects


def _load_rooms(rooms_path: str) -> dict:
    """
    Reads backend_new/data/rooms.xlsx
    Columns: room_id (col A) | [blank] | [blank] | capacity (col D)
    Room type derived from prefix: LH = lecture, CL = lab
    """
    print("\n  [2/3] Loading rooms.xlsx ...")
    wb = openpyxl.load_workbook(rooms_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]   # skip header

    rooms = {}
    for r in rows:
        if not any(c for c in r):
            continue
        rid = str(r[0]).strip() if r[0] else ""
        # Capacity is in column D (index 3) — two blank filler columns in between
        cap = 0
        if len(r) > 3 and r[3] is not None:
            try:
                cap = int(float(str(r[3])))
            except Exception:
                cap = 0

        if not rid or rid.lower() in ("nan", "room id", "room_id", ""):
            continue

        prefix    = rid.replace("-", "").replace(" ", "").upper()[:2]
        room_type = "lab" if prefix == "CL" else "lecture"

        if rid not in rooms:
            rooms[rid] = Room(room_id=rid, capacity=cap, room_type=room_type)

    lh = sum(1 for r in rooms.values() if r.room_type == "lecture")
    cl = sum(1 for r in rooms.values() if r.room_type == "lab")
    print(f"    ✓ {len(rooms)} rooms  ({lh} lecture halls, {cl} computer labs)")
    return rooms


def _load_students(wb) -> dict:
    """Reads Sheet1 from software_files.xlsx"""
    print("\n  [3/3] Loading students from Sheet1 ...")
    ws   = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))[1:]   # skip header

    students   = {}
    skipped    = 0
    sem_counts = defaultdict(int)

    for r in rows:
        if not any(c for c in r):
            continue

        enr = r[0]
        if enr is None:
            skipped += 1
            continue
        try:
            enr = str(int(float(str(enr))))
        except Exception:
            skipped += 1
            continue

        name     = str(r[1]).strip() if r[1] else ""
        email    = str(r[2]).strip() if r[2] else ""
        major    = _canonical(str(r[3]).strip() if r[3] else "")
        minor    = _canonical(str(r[4]).strip() if r[4] else "")
        try:
            semester = int(float(str(r[5])))
        except Exception:
            semester = 0

        if enr in students:
            print(f"    ⚠  Duplicate enrollment_no {enr} — skipping")
            continue

        students[enr] = Student(enrollment_no=enr, name=name, email=email,
                                major=major, minor=minor, semester=semester)
        sem_counts[semester] += 1

    if skipped:
        print(f"    ⚠  Skipped {skipped} blank/invalid rows")

    print(f"    ✓ {len(students)} students loaded")
    for sem, cnt in sorted(sem_counts.items()):
        print(f"      Semester {sem}: {cnt} students")
    return students


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment groups + conflict graph
# ─────────────────────────────────────────────────────────────────────────────

def _build_enrollment_groups(students, curriculum) -> dict:
    print("\n  Building enrollment groups ...")
    combos  = set()
    for s in students.values():
        combos.add((s.semester, s.major, s.minor))

    groups  = {}
    missing = set()

    for (semester, major, minor) in sorted(combos):
        codes = []

        major_entries = curriculum.get((major, semester), [])
        if not major_entries and major:
            missing.add(f"major='{major}' sem={semester}")
        for e in major_entries:
            if e.offered_as in ("major", "major/minor"):
                codes.append(e.course_code)

        if minor:
            minor_entries = curriculum.get((minor, semester), [])
            if not minor_entries:
                missing.add(f"minor='{minor}' sem={semester}")
            for e in minor_entries:
                if e.offered_as in ("minor", "major/minor"):
                    if e.course_code not in codes:
                        codes.append(e.course_code)

        # Deduplicate while preserving order
        groups[(semester, major, minor)] = list(dict.fromkeys(codes))

    if missing:
        print(f"    ⚠  No curriculum data for (groups will have 0 subjects):")
        for m in sorted(missing):
            print(f"      - {m}")

    active = sum(1 for v in groups.values() if v)
    print(f"    ✓ {len(groups)} enrollment groups total  |  {active} active (>0 subjects)")
    for (sem, maj, mn), codes in sorted(groups.items()):
        if codes:
            label = f"sem{sem} | {maj}" + (f" + {mn}" if mn else "")
            print(f"      {label:55s} → {len(codes)} subjects")

    return groups


def _build_conflict_graph(groups) -> dict:
    print("\n  Building conflict graph ...")
    from collections import defaultdict
    graph = defaultdict(set)
    for codes in groups.values():
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                a, b = codes[i], codes[j]
                graph[a].add(b)
                graph[b].add(a)
    graph = dict(graph)
    edges = sum(len(v) for v in graph.values()) // 2
    print(f"    ✓ {len(graph)} subjects in conflict graph  |  {edges} conflict edges")
    return graph


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate(students, curriculum, subjects, teacher_subjects):
    print("\n  Running validation ...")
    all_programs = {prog for (prog, _) in curriculum.keys()}

    no_teacher = [f"{c} ({subjects[c].title})"
                  for c in subjects if c not in teacher_subjects]
    if no_teacher:
        print(f"    ⚠  {len(no_teacher)} subjects with no teacher assigned:")
        for s in no_teacher:
            print(f"      - {s}")

    missing_prog = set()
    for s in students.values():
        if s.major and s.major not in all_programs:
            missing_prog.add(f"major '{s.major}' sem {s.semester}")
        if s.minor and s.minor not in all_programs:
            missing_prog.add(f"minor '{s.minor}' sem {s.semester}")
    if missing_prog:
        print(f"    ⚠  Programs in students not found in curriculum ({len(missing_prog)}):")
        for p in sorted(missing_prog):
            print(f"      - {p}")

    if not no_teacher and not missing_prog:
        print("    ✓ All checks passed.")


# ─────────────────────────────────────────────────────────────────────────────
# JSON serialiser
# ─────────────────────────────────────────────────────────────────────────────

def _to_json(data: dict) -> dict:
    def conv(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        if isinstance(obj, set):
            return sorted(list(obj))
        if isinstance(obj, dict):
            return {str(k): conv(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [conv(i) for i in obj]
        return obj

    return {
        "subjects":    conv(data["subjects"]),
        "teachers":    conv(data["teachers"]),
        "rooms":       conv(data["rooms"]),
        "students":    conv(data["students"]),
        "curriculum": {
            f"{prog}|sem{sem}": [asdict(e) for e in entries]
            for (prog, sem), entries in data["curriculum"].items()
        },
        "teacher_subjects": data["teacher_subjects"],
        "enrollment_groups": {
            f"sem{sem}|{maj}|{mn}": codes
            for (sem, maj, mn), codes in data["enrollment_groups"].items()
        },
        "conflict_graph": {
            k: sorted(v) for k, v in data["conflict_graph"].items()
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def load_data(software_xlsx: str, rooms_xlsx: str, output_json: str, active_semesters: list = None) -> dict:
    """
    Args:
        software_xlsx : path to backend_new/data/software_files.xlsx
        rooms_xlsx    : path to backend_new/data/rooms.xlsx
        output_json   : path to write extracted_data.json (in backend_new/output/)
    """
    print("=" * 65)
    print("  TSLAS DATA EXTRACTOR")
    print("=" * 65)

    wb = openpyxl.load_workbook(software_xlsx, read_only=True, data_only=True)

    curriculum, subjects, teachers, teacher_subjects = \
        _load_curriculum_and_teachers(wb)
    rooms    = _load_rooms(rooms_xlsx)
    students = _load_students(wb)

    # ── Filter students to active semesters only ──
    if active_semesters:
        before = len(students)
        students = {
            enr: s for enr, s in students.items()
            if s.semester in active_semesters
        }
        filtered = before - len(students)
        parity = 'even' if active_semesters[0] % 2 == 0 else 'odd'
        print(f"  Semester filter: {parity.upper()} {active_semesters}")
        print(f"  Students after filter: {len(students)}  ({filtered} excluded)")

    _validate(students, curriculum, subjects, teacher_subjects)

    enrollment_groups = _build_enrollment_groups(students, curriculum)
    conflict_graph    = _build_conflict_graph(enrollment_groups)

    data = {
        "subjects":          subjects,
        "teachers":          teachers,
        "rooms":             rooms,
        "students":          students,
        "curriculum":        curriculum,
        "teacher_subjects":  teacher_subjects,
        "enrollment_groups": enrollment_groups,
        "conflict_graph":    conflict_graph,
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(_to_json(data), f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved → {output_json}")

    print("\n" + "=" * 65)
    print("  EXTRACTION COMPLETE")
    print("=" * 65)
    parity_label = ""
    if active_semesters:
        p = 'EVEN' if active_semesters[0] % 2 == 0 else 'ODD'
        parity_label = f"  ({p} semesters: {active_semesters})"
    print(f"  Subjects          : {len(subjects)}")
    print(f"  Teachers          : {len(teachers)}")
    print(f"  Rooms             : {len(rooms)}")
    print(f"  Students          : {len(students)}{parity_label}")
    active = sum(1 for v in enrollment_groups.values() if v)
    print(f"  Enrollment groups : {len(enrollment_groups)}  ({active} active)")
    edges = sum(len(v) for v in conflict_graph.values()) // 2
    print(f"  Conflict edges    : {edges}")
    print("=" * 65)

    return data