"""
scheduler.py  v2
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  - Timeslots: 8:00–17:10, 50-min each, 11 slots/day, 55 total
  - Practicals (P > 0) occupy TWO consecutive slots in the same day
  - No lunch break hardcoded — slots run continuously
  - Solution state for practicals: {course_code → (slot_index, room_id)}
    where slot_index is the FIRST of the two consecutive slots
  - Penalty H4 added: practical not in consecutive slots (shouldn't happen
    with the new neighbour but kept as guard)
"""

import json
import math
import random
import copy
import os
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# Timeslots  —  08:00 to 17:10, 50 min each, Mon–Fri
# ─────────────────────────────────────────────────────────────────────────────

DAYS  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Generate 11 slots per day
_START_MIN    = 8 * 60          # 480
_SLOT_MINUTES = 50
_SLOTS_PER_DAY = 0
_TIMES = []
t = _START_MIN
while t + _SLOT_MINUTES <= 17 * 60 + 10:   # 1030
    h1, m1 = divmod(t, 60)
    h2, m2 = divmod(t + _SLOT_MINUTES, 60)
    _TIMES.append((f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"))
    t += _SLOT_MINUTES
SLOTS_PER_DAY  = len(_TIMES)    # 11
TOTAL_SLOTS    = SLOTS_PER_DAY * len(DAYS)   # 55

ALL_SLOTS = [
    {
        "slot_index": d * SLOTS_PER_DAY + s,
        "day":        day,
        "start":      start,
        "end":        end,
    }
    for d, day in enumerate(DAYS)
    for s, (start, end) in enumerate(_TIMES)
]

def slot_day(idx: int)  -> int: return idx // SLOTS_PER_DAY
def slot_time(idx: int) -> int: return idx  % SLOTS_PER_DAY
def last_slot_of_day(day_idx: int) -> int:
    return day_idx * SLOTS_PER_DAY + SLOTS_PER_DAY - 1

def valid_practical_slot(slot_idx: int) -> bool:
    """
    A practical starts at slot_idx and needs slot_idx+1 to exist
    AND both slots must be on the same day.
    So slot_idx cannot be the last slot of any day.
    """
    return slot_time(slot_idx) < SLOTS_PER_DAY - 1


# ─────────────────────────────────────────────────────────────────────────────
# Penalty weights
# ─────────────────────────────────────────────────────────────────────────────

W_H1 = 10000   # two conflicting subjects in same slot
W_H2 = 10000   # teacher double-booked
W_H3 = 10000   # room double-booked
W_H4 = 10000   # practical placed at last slot of day (no room for 2nd slot)
W_S1 = 200     # room capacity too small (per overflow student)
W_S2 = 100     # practical in non-lab room  /  lecture in lab room
W_S3 = 30      # teacher > 3 classes/day
W_S4 = 15      # student group spread > 4 slots in one day


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class TimetableScheduler:

    def __init__(self, data: dict):
        self.subjects          = data["subjects"]
        self.rooms             = data["rooms"]
        self.students          = data["students"]
        self.teacher_subjects  = data["teacher_subjects"]
        self.enrollment_groups = data["enrollment_groups"]
        self.conflict_sets     = {
            k: set(v) for k, v in data["conflict_graph"].items()
        }

        # Subjects to schedule = active in at least one group + have a teacher
        active_codes = set()
        for codes in self.enrollment_groups.values():
            active_codes.update(codes)
        self.schedulable = [
            c for c in active_codes
            if c in self.teacher_subjects and c in self.subjects
        ]

        # Identify practical subjects (P > 0 → needs 2 consecutive slots)
        self.is_practical = {
            c: (self.subjects[c].get("P", 0) > 0)
            for c in self.schedulable
        }

        # Room pools
        # NOTE: "lab" room_type = practical rooms (CL-1, CL-2)
        #       "lecture" room_type = regular lecture halls (LH1–LH16)
        # Practical subjects → lab rooms
        # Lecture/Tutorial subjects → lecture rooms
        self.lecture_rooms = [
            rid for rid, r in self.rooms.items() if r["room_type"] == "lecture"
        ]
        self.lab_rooms = [
            rid for rid, r in self.rooms.items() if r["room_type"] == "lab"
        ]
        self.all_rooms = list(self.rooms.keys())

        # Pre-compute required room type
        self.room_needed = {
            c: ("lab" if self.is_practical[c] else "lecture")
            for c in self.schedulable
        }

        # Pre-compute student count per subject
        self.student_counts = defaultdict(int)
        for s in self.students.values():
            key   = f"sem{s['semester']}|{s['major']}|{s['minor']}"
            codes = self.enrollment_groups.get(key, [])
            for c in codes:
                self.student_counts[c] += 1

        # Group membership sets for S4
        self.group_code_sets = {
            k: set(v) for k, v in self.enrollment_groups.items() if v
        }

        # Valid starting slots for practicals (not last slot of any day)
        self.valid_practical_starts = [
            i for i in range(TOTAL_SLOTS) if valid_practical_slot(i)
        ]
        self.valid_lecture_slots = list(range(TOTAL_SLOTS))

        print(f"\n  Subjects to schedule  : {len(self.schedulable)}")
        lec = sum(1 for c in self.schedulable if not self.is_practical[c])
        prac = sum(1 for c in self.schedulable if self.is_practical[c])
        print(f"    Lectures/Tutorials  : {lec}")
        print(f"    Practicals (2-slot) : {prac}")
        print(f"  Total slots           : {TOTAL_SLOTS}  "
              f"({len(DAYS)} days × {SLOTS_PER_DAY} slots/day)")
        print(f"  Rooms                 : {len(self.rooms)}  "
              f"({len(self.lecture_rooms)} lecture, {len(self.lab_rooms)} lab)")
        print(f"  Active student groups : {len(self.group_code_sets)}")
        print(f"  Conflict edges        : "
              f"{sum(len(v) for v in self.conflict_sets.values()) // 2}")


    # ── Initial solution ─────────────────────────────────────────────────

    def _random_solution(self) -> dict:
        """
        Assigns each subject a random (slot_index, room_id).
        For practicals: slot_index is the FIRST of two consecutive slots.
        Slot index stored is always the starting slot.
        """
        sol = {}
        for code in self.schedulable:
            if self.is_practical[code]:
                slot = random.choice(self.valid_practical_starts)
                pool = self.lab_rooms or self.all_rooms
            else:
                slot = random.randint(0, TOTAL_SLOTS - 1)
                pool = self.lecture_rooms or self.all_rooms
            sol[code] = (slot, random.choice(pool))
        return sol


    # ── Penalty ──────────────────────────────────────────────────────────

    def _penalty(self, sol: dict) -> int:
        pen = 0

        # Expand solution: for each subject, list ALL slot indices it occupies
        # Lecture = 1 slot, Practical = 2 consecutive slots
        def occupied_slots(code, start_slot):
            if self.is_practical[code]:
                return [start_slot, start_slot + 1]
            return [start_slot]

        # Build expanded indexes
        # slot → [(code, room)]
        slot_occupancy = defaultdict(list)
        teacher_slots  = defaultdict(list)   # teacher → [slot_idx, ...]
        teacher_day    = defaultdict(lambda: defaultdict(int))  # teacher → {day: count}

        for code, (start_slot, room) in sol.items():
            slots = occupied_slots(code, start_slot)
            for slot in slots:
                slot_occupancy[slot].append((code, room))
            t = self.teacher_subjects.get(code)
            if t:
                for slot in slots:
                    teacher_day[t][slot_day(slot)] += 1
                # For teacher double-booking we track unique slots
                for slot in set(slots):
                    teacher_slots[t].append(slot)

        # H4 — practical placed at last slot of day (2nd slot would overflow)
        for code, (start_slot, room) in sol.items():
            if self.is_practical[code] and not valid_practical_slot(start_slot):
                pen += W_H4

        # H1 — conflicting subjects sharing any slot
        for slot, entries in slot_occupancy.items():
            codes_here = [e[0] for e in entries]
            n = len(codes_here)
            for i in range(n):
                for j in range(i + 1, n):
                    # Only penalise if they are different subjects
                    if codes_here[i] != codes_here[j]:
                        if codes_here[j] in self.conflict_sets.get(codes_here[i], set()):
                            pen += W_H1

        # H2 — teacher double-booked in any single slot
        slot_teachers = defaultdict(list)
        for code, (start_slot, room) in sol.items():
            t = self.teacher_subjects.get(code)
            if t:
                for slot in occupied_slots(code, start_slot):
                    slot_teachers[slot].append(t)
        for slot, teachers in slot_teachers.items():
            seen = set()
            for t in teachers:
                if t in seen:
                    pen += W_H2
                seen.add(t)

        # H3 — room double-booked in any single slot
        for slot, entries in slot_occupancy.items():
            rooms_here = [e[1] for e in entries]
            seen = set()
            for r in rooms_here:
                if r in seen:
                    pen += W_H3
                seen.add(r)

        # S1 — room too small
        for code, (start_slot, room) in sol.items():
            students = self.student_counts.get(code, 0)
            cap      = self.rooms[room]["capacity"]
            if students > cap:
                pen += W_S1 * (students - cap)

        # S2 — wrong room type
        for code, (start_slot, room) in sol.items():
            if self.room_needed.get(code, "lecture") != self.rooms[room]["room_type"]:
                pen += W_S2

        # S3 — teacher > 3 occupied slots per day
        # For practicals a teacher teaches 2 slots but counts as 1 class
        teacher_class_day = defaultdict(lambda: defaultdict(int))
        for code, (start_slot, room) in sol.items():
            t = self.teacher_subjects.get(code)
            if t:
                teacher_class_day[t][slot_day(start_slot)] += 1
        for t, days in teacher_class_day.items():
            for d, cnt in days.items():
                if cnt > 3:
                    pen += W_S3 * (cnt - 3)

        # S4 — student group spread > 4 slots in one day
        for group_key, codes_set in self.group_code_sets.items():
            day_times = defaultdict(list)
            for code, (start_slot, room) in sol.items():
                if code in codes_set:
                    for slot in occupied_slots(code, start_slot):
                        day_times[slot_day(slot)].append(slot_time(slot))
            for d, times in day_times.items():
                if len(times) >= 2:
                    times.sort()
                    if times[-1] - times[0] > 6:   # wider threshold for 11-slot days
                        pen += W_S4

        return pen


    # ── Neighbour moves ──────────────────────────────────────────────────

    def _neighbour(self, sol: dict) -> dict:
        """
        Three move types:
          0 — Reassign one subject to new (slot, room)
          1 — Swap starting slots between two subjects
          2 — Change room only for one subject
        For practicals, always pick from valid_practical_starts.
        """
        new   = sol.copy()
        codes = list(new.keys())
        move  = random.randint(0, 2)

        if move == 0 or len(codes) < 2:
            code = random.choice(codes)
            if self.is_practical[code]:
                slot = random.choice(self.valid_practical_starts)
                pool = self.lab_rooms or self.all_rooms
            else:
                slot = random.randint(0, TOTAL_SLOTS - 1)
                pool = self.lecture_rooms or self.all_rooms
            new[code] = (slot, random.choice(pool))

        elif move == 1:
            a, b = random.sample(codes, 2)
            sa, ra = new[a]
            sb, rb = new[b]
            # Validate swap: if a is practical, sb must be a valid practical start
            # and vice versa
            new_sa = sb
            new_sb = sa
            if self.is_practical[a] and not valid_practical_slot(new_sa):
                new_sa = random.choice(self.valid_practical_starts)
            if self.is_practical[b] and not valid_practical_slot(new_sb):
                new_sb = random.choice(self.valid_practical_starts)
            new[a] = (new_sa, ra)
            new[b] = (new_sb, rb)

        else:
            code = random.choice(codes)
            slot = new[code][0]
            if self.is_practical[code]:
                pool = self.lab_rooms or self.all_rooms
            else:
                pool = self.lecture_rooms or self.all_rooms
            new[code] = (slot, random.choice(pool))

        return new


    # ── Simulated Annealing ──────────────────────────────────────────────

    def solve(
        self,
        initial_temp:      float = 50000.0,
        cooling_rate:      float = 0.9997,
        min_temp:          float = 1.0,
        iters_per_temp:    int   = 100,
        restart_threshold: int   = 3000,
    ) -> dict:

        print(f"\n  Simulated Annealing")
        print(f"  T₀={initial_temp}  cooling={cooling_rate}  "
              f"min_T={min_temp}  iters/step={iters_per_temp}")

        current     = self._random_solution()
        current_pen = self._penalty(current)
        best        = copy.copy(current)
        best_pen    = current_pen
        temp        = initial_temp
        step        = 0
        no_improve  = 0

        print(f"  Initial penalty : {current_pen}\n")

        while temp > min_temp and best_pen > 0:
            for _ in range(iters_per_temp):
                nb    = self._neighbour(current)
                nb_p  = self._penalty(nb)
                delta = nb_p - current_pen
                if delta < 0 or random.random() < math.exp(-delta / temp):
                    current, current_pen = nb, nb_p
                    if current_pen < best_pen:
                        best, best_pen = copy.copy(current), current_pen
                        no_improve = 0

            temp      *= cooling_rate
            step      += 1
            no_improve += 1

            if no_improve >= restart_threshold:
                current, current_pen = copy.copy(best), best_pen
                no_improve = 0
                print(f"  ↺ Restart at step {step}  (best={best_pen})")

            if step % 200 == 0:
                print(f"  Step {step:6d}  T={temp:9.2f}  "
                      f"best={best_pen:6d}  current={current_pen:6d}")

        print(f"\n  ── SA complete ───────────────────────────────")
        print(f"  Steps        : {step}")
        print(f"  Final penalty: {best_pen}")
        if best_pen == 0:
            print("  ✓ Perfect solution — zero violations")
        else:
            print("  ⚠ Remaining violations:")
            self._print_violations(best)
        return best


    def _print_violations(self, sol):
        def occupied(code, s):
            return [s, s+1] if self.is_practical[code] else [s]

        slot_occ = defaultdict(list)
        for code, (s, r) in sol.items():
            for slot in occupied(code, s):
                slot_occ[slot].append(code)

        h1 = h2 = h3 = h4 = 0
        for code, (s, r) in sol.items():
            if self.is_practical[code] and not valid_practical_slot(s):
                h4 += 1
                print(f"    H4 PRACTICAL AT DAY-END: {code} at slot {s}")

        for slot, codes in slot_occ.items():
            n = len(codes)
            for i in range(n):
                for j in range(i+1, n):
                    if codes[i] != codes[j] and \
                       codes[j] in self.conflict_sets.get(codes[i], set()):
                        h1 += 1
                        sl = ALL_SLOTS[slot]
                        print(f"    H1 CLASH: {codes[i]} ↔ {codes[j]} "
                              f"at {sl['day']} {sl['start']}")
            seen = set()
            for c in codes:
                t = self.teacher_subjects.get(c)
                if t:
                    if t in seen:
                        h2 += 1
                        print(f"    H2 TEACHER: {t} double at "
                              f"{ALL_SLOTS[slot]['day']} {ALL_SLOTS[slot]['start']}")
                    seen.add(t)
            rooms_h = [sol[c][1] for c in codes]
            seen = set()
            for rr in rooms_h:
                if rr in seen: h3 += 1
                seen.add(rr)

        print(f"    H1 student clashes  : {h1}")
        print(f"    H2 teacher clashes  : {h2}")
        print(f"    H3 room clashes     : {h3}")
        print(f"    H4 practical at EOD : {h4}")


# ─────────────────────────────────────────────────────────────────────────────
# Build output JSON
# ─────────────────────────────────────────────────────────────────────────────

def build_timetable_json(solution: dict, data: dict) -> dict:
    subjects         = data["subjects"]
    rooms            = data["rooms"]
    teacher_subjects = data["teacher_subjects"]
    students         = data["students"]
    groups           = data["enrollment_groups"]

    # Determine which subjects are practicals
    is_practical = {
        c: (subjects.get(c, {}).get("P", 0) > 0)
        for c in solution
    }

    day_order = {d: i for i, d in enumerate(DAYS)}
    classes   = []

    for code, (start_slot, room_id) in solution.items():
        subj = subjects.get(code, {})
        room = rooms.get(room_id, {})
        slot1 = ALL_SLOTS[start_slot]

        if is_practical[code]:
            # Practical spans two consecutive slots
            slot2 = ALL_SLOTS[start_slot + 1]
            end_time = slot2["end"]
            slot_count = 2
        else:
            end_time   = slot1["end"]
            slot_count = 1

        classes.append({
            "course_code":  code,
            "title":        subj.get("title", ""),
            "credits":      subj.get("credits", 0),
            "type":         "practical" if is_practical[code] else "lecture",
            "slots":        slot_count,
            "day":          slot1["day"],
            "start":        slot1["start"],
            "end":          end_time,
            "slot_index":   start_slot,
            "room_id":      room_id,
            "room_type":    room.get("room_type", ""),
            "capacity":     room.get("capacity", 0),
            "teacher":      teacher_subjects.get(code, "TBA"),
        })

    classes.sort(key=lambda c: (day_order[c["day"]], c["slot_index"]))

    by_day = {day: [c for c in classes if c["day"] == day] for day in DAYS}

    by_student = {}
    for enr, s in students.items():
        key      = f"sem{s['semester']}|{s['major']}|{s['minor']}"
        my_codes = set(groups.get(key, []))
        my_cls   = [c for c in classes if c["course_code"] in my_codes]
        by_student[enr] = {
            "enrollment_no": enr,
            "name":          s["name"],
            "email":         s["email"],
            "major":         s["major"],
            "minor":         s["minor"],
            "semester":      s["semester"],
            "classes":       my_cls,
        }

    return {
        "meta": {
            "total_classes":  len(classes),
            "total_students": len(by_student),
            "days":           DAYS,
            "slots_per_day":  SLOTS_PER_DAY,
            "slot_duration_minutes": _SLOT_MINUTES,
            "timeslots":      ALL_SLOTS,
        },
        "timetable":  classes,
        "by_day":     by_day,
        "by_student": by_student,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run(
    extracted_json:    str,
    output_json:       str,
    initial_temp:      float = 50000.0,
    cooling_rate:      float = 0.9997,
    min_temp:          float = 1.0,
    iters_per_temp:    int   = 100,
    restart_threshold: int   = 3000,
) -> dict:

    print("=" * 65)
    print("  TSLAS TIMETABLE SCHEDULER  v2  —  Simulated Annealing")
    print("=" * 65)

    with open(extracted_json, encoding="utf-8") as f:
        raw = json.load(f)

    data = {
        "subjects":          raw["subjects"],
        "rooms":             raw["rooms"],
        "students":          raw["students"],
        "teacher_subjects":  raw["teacher_subjects"],
        "enrollment_groups": raw["enrollment_groups"],
        "conflict_graph":    {k: set(v) for k, v in raw["conflict_graph"].items()},
    }

    sched    = TimetableScheduler(data)
    solution = sched.solve(
        initial_temp      = initial_temp,
        cooling_rate      = cooling_rate,
        min_temp          = min_temp,
        iters_per_temp    = iters_per_temp,
        restart_threshold = restart_threshold,
    )

    out = build_timetable_json(solution, data)

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\n  ✓ Saved → {output_json}")
    print(f"  Classes  : {out['meta']['total_classes']}")
    print(f"  Students : {out['meta']['total_students']}")

    # Print 2 sample student timetables
    printed = 0
    for enr, s in out["by_student"].items():
        if s["classes"] and len(s["classes"]) >= 3:
            print(f"\n  ── {s['name']} ({enr})  "
                  f"sem{s['semester']}  {s['major']} + {s['minor']}")
            for c in s["classes"]:
                typ = "PRAC" if c["type"] == "practical" else "LEC "
                print(f"     {c['day']:10s}  {c['start']}–{c['end']}"
                      f"  [{typ}]  {c['course_code']:10s}"
                      f"  {c['title'][:34]:34s}"
                      f"  [{c['room_id']:6s}]  {c['teacher']}")
            printed += 1
            if printed == 2:
                break
    return out