"""
scheduler.py  v3
─────────────────────────────────────────────────────────────────────────────
Schedules SchedulableUnits (unit_ids), not course_codes.
Each unit_id is one class session, e.g. TB2401_L1, TB2401_L2, TA2405_P1.
Practicals (unit_type=practical) occupy 2 consecutive slots.
"""

import json
import math
import random
import copy
import os
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# Timeslots — 08:00 to 18:50, 50-min slots, Mon–Fri
#
# 13 slots/day (was 11): the range was extended by 2 slots at the end of
# the day. One of those 13 slots — 13:00-13:50 (1:00pm-1:50pm) — is a
# fixed LUNCH BREAK and is never used for scheduling classes.
# ─────────────────────────────────────────────────────────────────────────────

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_SLOT_MINUTES = 50
_DAY_END_MIN  = 18 * 60 + 50   # 18:50 → last slot ends at 6:50pm
_TIMES = []
t = 8 * 60
while t + _SLOT_MINUTES <= _DAY_END_MIN:
    h1, m1 = divmod(t, 60)
    h2, m2 = divmod(t + _SLOT_MINUTES, 60)
    _TIMES.append((f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"))
    t += _SLOT_MINUTES

SLOTS_PER_DAY = len(_TIMES)
TOTAL_SLOTS   = SLOTS_PER_DAY * len(DAYS)

# Which slot-of-day is the lunch break (13:00-13:50)?
LUNCH_START = "13:00"
LUNCH_SLOT_TIME = next(
    (i for i, (start, _end) in enumerate(_TIMES) if start == LUNCH_START), None
)
if LUNCH_SLOT_TIME is None:
    raise RuntimeError(
        f"Lunch start time {LUNCH_START} does not align with any timeslot boundary."
    )

ALL_SLOTS = [
    {
        "slot_index": d * SLOTS_PER_DAY + s,
        "day": day, "start": start, "end": end,
        "is_lunch": (s == LUNCH_SLOT_TIME),
    }
    for d, day in enumerate(DAYS)
    for s, (start, end) in enumerate(_TIMES)
]

def slot_day(idx):  return idx // SLOTS_PER_DAY
def slot_time(idx): return idx  % SLOTS_PER_DAY
def is_lunch_slot(idx): return slot_time(idx) == LUNCH_SLOT_TIME

def valid_practical_slot(idx):
    # Must leave room for the 2nd half within the same day, and must not
    # start on, or span across, the lunch break.
    if slot_time(idx) >= SLOTS_PER_DAY - 1:
        return False
    if is_lunch_slot(idx) or is_lunch_slot(idx + 1):
        return False
    return True

# Every non-lunch slot in the week — the only slots lectures/tutorials may
# ever be placed in.
SCHEDULABLE_SLOTS = [i for i in range(TOTAL_SLOTS) if not is_lunch_slot(i)]

# ─────────────────────────────────────────────────────────────────────────────
# Penalty weights
# ─────────────────────────────────────────────────────────────────────────────

W_H1 = 10000
W_H2 = 10000
W_H3 = 10000
W_H4 = 10000
W_S1 = 200
W_S2 = 100
W_S3 = 30
W_S4 = 15
W_S5 = 20
W_S6 = 50     # student group has more than MAX_DAILY_SESSIONS in one day
W_H5 = 10000  # unit placed on/over the lunch break slot (should never
              # happen given SCHEDULABLE_SLOTS/valid_practical_slot, but
              # kept as a defensive hard-constraint check)

MAX_DAILY_SESSIONS = 8


class TimetableScheduler:

    def __init__(self, data):
        self.subjects          = data["subjects"]
        self.units              = data["units"]
        self.rooms              = data["rooms"]
        self.students           = data["students"]
        self.teacher_subjects   = data["teacher_subjects"]
        self.enrollment_groups  = data["enrollment_groups"]
        self.conflict_sets      = {k: set(v) for k, v in data["conflict_graph"].items()}

        active_units = set()
        for uids in self.enrollment_groups.values():
            active_units.update(uids)

        self.schedulable = [
            uid for uid in active_units
            if uid in self.units
            and self.units[uid]["course_code"] in self.teacher_subjects
        ]

        self.lecture_rooms = [rid for rid, r in self.rooms.items() if r["room_type"] == "lecture"]
        self.lab_rooms     = [rid for rid, r in self.rooms.items() if r["room_type"] == "lab"]
        self.all_rooms     = list(self.rooms.keys())

        self.student_counts = defaultdict(int)
        for s in self.students.values():
            key  = f"sem{s['semester']}|{s['major']}|{s['minor']}"
            uids = self.enrollment_groups.get(key, [])
            seen_codes = set()
            for uid in uids:
                code = self.units[uid]["course_code"]
                if code not in seen_codes:
                    self.student_counts[code] += 1
                    seen_codes.add(code)

        self.room_needed = {
            uid: ("lab" if self.units[uid]["unit_type"] == "practical" else "lecture")
            for uid in self.schedulable
        }

        self.group_unit_sets = {
            k: set(v) for k, v in self.enrollment_groups.items() if v
        }

        self.valid_practical_starts = [
            i for i in range(TOTAL_SLOTS) if valid_practical_slot(i)
        ]

        self.code_to_units = defaultdict(list)
        for uid in self.schedulable:
            self.code_to_units[self.units[uid]["course_code"]].append(uid)

        # ── Precompute conflict pairs as a flat list for fast penalty calc ──
        # This avoids rebuilding slot indexes from scratch every penalty call.
        self._uid_list = self.schedulable

        lec  = sum(1 for uid in self.schedulable if self.units[uid]["unit_type"] == "lecture")
        tut  = sum(1 for uid in self.schedulable if self.units[uid]["unit_type"] == "tutorial")
        prac = sum(1 for uid in self.schedulable if self.units[uid]["unit_type"] == "practical")

        print(f"\n  Units to schedule     : {len(self.schedulable)}")
        print(f"    Lectures            : {lec}")
        print(f"    Tutorials           : {tut}")
        print(f"    Practicals (2-slot) : {prac}")
        print(f"  Slot-entries needed   : {lec + tut + prac*2}")
        print(f"  Total slots available : {TOTAL_SLOTS}  ({len(DAYS)} × {SLOTS_PER_DAY})")
        print(f"  Room-slots available  : {TOTAL_SLOTS * len(self.rooms)}")
        print(f"  Active groups         : {len(self.group_unit_sets)}")
        print(f"  Conflict edges        : {sum(len(v) for v in self.conflict_sets.values()) // 2}")


    def _random_solution(self):
        sol = {}
        for uid in self.schedulable:
            unit = self.units[uid]
            if unit["unit_type"] == "practical":
                slot = random.choice(self.valid_practical_starts)
                pool = self.lab_rooms or self.all_rooms
            else:
                slot = random.choice(SCHEDULABLE_SLOTS)
                pool = self.lecture_rooms or self.all_rooms
            sol[uid] = (slot, random.choice(pool))
        return sol


    def _greedy_solution(self):
        """
        Constructive initial solution: place units one at a time, each time
        picking the (slot, room) that creates the FEWEST new hard-constraint
        violations against units already placed. This starts SA much closer
        to a feasible solution than pure random placement, which is critical
        once the conflict graph gets large (thousands of edges).

        Units are placed in order of "most constrained first" — units
        belonging to the largest enrollment groups go first, since they
        have the most potential conflicts and are hardest to place later.
        """
        sol = {}

        # Order: units in subjects that appear in more groups go first
        # (rough proxy: how many conflict edges this unit already has)
        order = sorted(
            self.schedulable,
            key=lambda uid: -len(self.conflict_sets.get(uid, set()))
        )

        # Track occupancy as we place units, for fast incremental checks
        slot_units_used  = defaultdict(set)   # slot -> {uid}
        slot_rooms_used  = defaultdict(set)   # slot -> {room_id}
        teacher_slot_used = defaultdict(set)  # teacher -> {slot}

        def occ(uid, start):
            return (start, start + 1) if self.units[uid]["unit_type"] == "practical" else (start,)

        for uid in order:
            unit = self.units[uid]
            is_prac = unit["unit_type"] == "practical"
            teacher = self.teacher_subjects.get(unit["course_code"])
            pool    = (self.lab_rooms if is_prac else self.lecture_rooms) or self.all_rooms
            starts  = self.valid_practical_starts if is_prac else SCHEDULABLE_SLOTS

            best_choice = None
            best_score  = None

            # Sample a subset of candidate slots/rooms rather than all —
            # full enumeration (55 slots x 18 rooms) per unit is cheap enough
            # here (242 units), so we check every slot but only a few rooms.
            sample_rooms = random.sample(pool, min(4, len(pool)))

            for start in starts:
                slots = occ(uid, start)

                # Hard check 1: student clash — any conflicting uid already in these slots?
                clash = False
                for s in slots:
                    for other_uid in slot_units_used[s]:
                        if other_uid in self.conflict_sets.get(uid, set()):
                            clash = True
                            break
                    if clash:
                        break
                if clash:
                    continue

                # Hard check 2: teacher clash
                if teacher:
                    if any(s in teacher_slot_used[teacher] for s in slots):
                        continue

                for room in sample_rooms:
                    # Hard check 3: room clash
                    if any(room in slot_rooms_used[s] for s in slots):
                        continue

                    # Found a fully feasible (start, room) — take it immediately
                    best_choice = (start, room)
                    break

                if best_choice:
                    break

            if best_choice is None:
                # No fully clash-free slot found (can happen if conflict
                # graph is very dense) — fall back to random; SA will fix
                # remaining violations afterwards.
                start = random.choice(list(starts))
                room  = random.choice(pool)
                best_choice = (start, room)

            start, room = best_choice
            sol[uid] = (start, room)
            for s in occ(uid, start):
                slot_units_used[s].add(uid)
                slot_rooms_used[s].add(room)
                if teacher:
                    teacher_slot_used[teacher].add(s)

        return sol


    def _penalty(self, sol, return_breakdown=False):
        hard_pen = 0
        soft_pen = 0

        def occupied(uid, start):
            return [start, start + 1] if self.units[uid]["unit_type"] == "practical" else [start]

        slot_units  = defaultdict(list)
        slot_rooms  = defaultdict(list)
        teacher_day = defaultdict(lambda: defaultdict(int))

        for uid, (start, room) in sol.items():
            for slot in occupied(uid, start):
                slot_units[slot].append(uid)
                slot_rooms[slot].append(room)
            teacher = self.teacher_subjects.get(self.units[uid]["course_code"])
            if teacher:
                teacher_day[teacher][slot_day(start)] += 1

        for uid, (start, room) in sol.items():
            if self.units[uid]["unit_type"] == "practical" and not valid_practical_slot(start):
                hard_pen += W_H4

        for uid, (start, room) in sol.items():
            is_prac = self.units[uid]["unit_type"] == "practical"
            if is_lunch_slot(start) or (is_prac and is_lunch_slot(start + 1)):
                hard_pen += W_H5

        for slot, uids in slot_units.items():
            n = len(uids)
            for i in range(n):
                for j in range(i + 1, n):
                    if uids[j] in self.conflict_sets.get(uids[i], set()):
                        hard_pen += W_H1

        for slot, uids in slot_units.items():
            seen = set()
            for uid in uids:
                t = self.teacher_subjects.get(self.units[uid]["course_code"])
                if t:
                    if t in seen: hard_pen += W_H2
                    seen.add(t)

        for slot, rooms_in_slot in slot_rooms.items():
            seen = set()
            for r in rooms_in_slot:
                if r in seen: hard_pen += W_H3
                seen.add(r)

        for uid, (start, room) in sol.items():
            code     = self.units[uid]["course_code"]
            students = self.student_counts.get(code, 0)
            cap      = self.rooms[room]["capacity"]
            if students > cap:
                soft_pen += W_S1 * (students - cap)

        for uid, (start, room) in sol.items():
            if self.room_needed.get(uid, "lecture") != self.rooms[room]["room_type"]:
                soft_pen += W_S2

        for teacher, days in teacher_day.items():
            for d, cnt in days.items():
                if cnt > 3:
                    soft_pen += W_S3 * (cnt - 3)

        for group_key, uid_set in self.group_unit_sets.items():
            day_times = defaultdict(list)
            for uid, (start, room) in sol.items():
                if uid in uid_set:
                    for slot in occupied(uid, start):
                        day_times[slot_day(slot)].append(slot_time(slot))
            for d, times in day_times.items():
                if len(times) >= 2:
                    times.sort()
                    if times[-1] - times[0] > 6:
                        soft_pen += W_S4

        for code, uids in self.code_to_units.items():
            if len(uids) < 2: continue
            day_counts = defaultdict(int)
            for uid in uids:
                if uid in sol:
                    day_counts[slot_day(sol[uid][0])] += 1
            for d, cnt in day_counts.items():
                if cnt > 1:
                    soft_pen += W_S5 * (cnt - 1)

        # S6 — student group has more than MAX_DAILY_SESSIONS sessions in
        # one day. This counts sessions, not slot-span (different from S4
        # which checks the gap between first and last session of the day).
        for group_key, uid_set in self.group_unit_sets.items():
            day_session_count = defaultdict(int)
            for uid, (start, room) in sol.items():
                if uid in uid_set:
                    day_session_count[slot_day(start)] += 1
            for d, cnt in day_session_count.items():
                if cnt > MAX_DAILY_SESSIONS:
                    soft_pen += W_S6 * (cnt - MAX_DAILY_SESSIONS)

        if return_breakdown:
            return hard_pen, soft_pen
        return hard_pen + soft_pen


    def _find_violating_units(self, sol):
        """
        Returns a list of unit_ids that are CURRENTLY involved in at least
        one hard-constraint violation (student/teacher/room clash).
        Used to bias the neighbour move towards fixing actual problems
        instead of picking purely randomly — this is what makes SA converge
        fast even when the conflict graph is dense.
        """
        def occupied(uid, start):
            return [start, start + 1] if self.units[uid]["unit_type"] == "practical" else [start]

        slot_units = defaultdict(list)
        slot_rooms = defaultdict(list)
        for uid, (start, room) in sol.items():
            for slot in occupied(uid, start):
                slot_units[slot].append(uid)
                slot_rooms[slot].append((uid, room))

        bad = set()
        for slot, uids in slot_units.items():
            n = len(uids)
            for i in range(n):
                for j in range(i + 1, n):
                    if uids[j] in self.conflict_sets.get(uids[i], set()):
                        bad.add(uids[i]); bad.add(uids[j])

            teacher_seen = {}
            for uid in uids:
                t = self.teacher_subjects.get(self.units[uid]["course_code"])
                if t:
                    if t in teacher_seen:
                        bad.add(uid); bad.add(teacher_seen[t])
                    teacher_seen[t] = uid

        for slot, pairs in slot_rooms.items():
            room_seen = {}
            for uid, room in pairs:
                if room in room_seen:
                    bad.add(uid); bad.add(room_seen[room])
                room_seen[room] = uid

        return list(bad)


    def _neighbour(self, sol, violating_uids=None):
        """
        Move selection: 70% of the time, if there are units currently in a
        hard-constraint violation, pick the unit to move FROM that set
        instead of uniformly at random. This is a guided/focused local
        search move — it concentrates effort on actually broken units
        rather than wasting moves on units that are already fine.
        """
        new  = sol.copy()
        uids = list(new.keys())

        use_guided = violating_uids and len(violating_uids) > 0 and random.random() < 0.7
        pool_uids  = violating_uids if use_guided else uids

        move = random.randint(0, 2)

        if move == 0 or len(uids) < 2:
            uid  = random.choice(pool_uids)
            unit = self.units[uid]
            if unit["unit_type"] == "practical":
                slot = random.choice(self.valid_practical_starts)
                pool = self.lab_rooms or self.all_rooms
            else:
                slot = random.choice(SCHEDULABLE_SLOTS)
                pool = self.lecture_rooms or self.all_rooms
            new[uid] = (slot, random.choice(pool))

        elif move == 1:
            a = random.choice(pool_uids)
            b = random.choice(uids)
            while b == a:
                b = random.choice(uids)
            sa, ra = new[a]
            sb, rb = new[b]
            new_sa, new_sb = sb, sa
            if self.units[a]["unit_type"] == "practical" and not valid_practical_slot(new_sa):
                new_sa = random.choice(self.valid_practical_starts)
            if self.units[b]["unit_type"] == "practical" and not valid_practical_slot(new_sb):
                new_sb = random.choice(self.valid_practical_starts)
            new[a] = (new_sa, ra)
            new[b] = (new_sb, rb)

        else:
            uid  = random.choice(pool_uids)
            slot = new[uid][0]
            pool = self.lab_rooms if self.units[uid]["unit_type"] == "practical" else self.lecture_rooms
            pool = pool or self.all_rooms
            new[uid] = (slot, random.choice(pool))

        return new


    def solve(self, initial_temp=10000.0, cooling_rate=0.995,
              min_temp=1.0, iters_per_temp=50, restart_threshold=500,
              max_steps=None, polish_iters=5000, verbose=True):

        if verbose:
            print(f"\n  Simulated Annealing")
            print(f"  T₀={initial_temp}  cooling={cooling_rate}  "
                  f"min_T={min_temp}  iters/step={iters_per_temp}")

        current        = self._greedy_solution()
        cur_hard, cur_soft = self._penalty(current, return_breakdown=True)
        current_pen    = cur_hard + cur_soft
        best           = copy.copy(current)
        best_hard      = cur_hard
        best_soft      = cur_soft
        best_pen       = current_pen
        temp           = initial_temp
        step           = 0
        no_improve     = 0

        if verbose:
            print(f"  Initial penalty : {current_pen}  "
                  f"(hard={cur_hard}, soft={cur_soft})\n")

        violating = self._find_violating_units(current)

        # STOP CONDITION: hard penalty must reach exactly 0 — this is the
        # correct check. Total penalty (hard+soft) can stay high forever
        # because soft penalties (room capacity, teacher load, day-spread)
        # often cannot reach 0 even in a perfectly valid timetable.
        while temp > min_temp and best_hard > 0:
            if max_steps and step >= max_steps:
                if verbose: print(f"  ⏱ Max steps ({max_steps}) reached, stopping.")
                break

            for _ in range(iters_per_temp):
                nb = self._neighbour(current, violating_uids=violating)
                nb_hard, nb_soft = self._penalty(nb, return_breakdown=True)
                nb_pen = nb_hard + nb_soft
                delta  = nb_pen - current_pen

                if delta < 0 or random.random() < math.exp(-delta / temp):
                    current, current_pen = nb, nb_pen
                    cur_hard, cur_soft = nb_hard, nb_soft

                    # "Better" is primarily about hard penalty; only compare
                    # soft penalty once hard is tied, so the search never
                    # trades away a hard-constraint fix for a soft gain.
                    is_better = (cur_hard < best_hard) or \
                                (cur_hard == best_hard and current_pen < best_pen)
                    if is_better:
                        best, best_hard, best_soft, best_pen = \
                            copy.copy(current), cur_hard, cur_soft, current_pen
                        no_improve = 0

            violating = self._find_violating_units(current)

            temp       *= cooling_rate
            step       += 1
            no_improve += 1

            if no_improve >= restart_threshold:
                current, current_pen = copy.copy(best), best_pen
                cur_hard, cur_soft   = best_hard, best_soft
                no_improve = 0
                violating  = self._find_violating_units(current)
                if verbose: print(f"  ↺ Restart at step {step}  "
                                  f"(best_hard={best_hard}, best_soft={best_soft})")

            if verbose and step % 100 == 0:
                print(f"  Step {step:6d}  T={temp:9.2f}  "
                      f"hard={cur_hard:5d}  soft={cur_soft:6d}  "
                      f"best_hard={best_hard:5d}  best_soft={best_soft:6d}")

        if verbose:
            print(f"\n  ── SA complete ──────────────────────────────────")
            print(f"  Steps        : {step}")
            print(f"  Final hard penalty: {best_hard}")
            print(f"  Final soft penalty: {best_soft}")
            if best_hard == 0:
                print("  ✓ ALL HARD CONSTRAINTS SATISFIED — "
                      "zero student/teacher/room/practical clashes")
                print(f"  ⚠ Soft penalty remaining: {best_soft} "
                      f"(room capacity / teacher load / day spread — "
                      f"expected, not fixable by scheduling alone)")
            else:
                print("  ⚠ HARD violations remain — did not converge:")
                self._print_violations(best)

        # ── Soft-penalty polishing pass ──────────────────────────────────
        # Once hard constraints are satisfied, spend a fixed extra budget
        # of iterations trying to reduce soft penalty WITHOUT ever
        # reintroducing a hard violation. Any move that would create a
        # hard violation is rejected outright, regardless of temperature.
        if best_hard == 0 and polish_iters > 0:
            if verbose:
                print(f"\n  Polishing soft penalty for {polish_iters} iterations...")
            polish_current      = copy.copy(best)
            polish_hard, polish_soft = best_hard, best_soft
            for _ in range(polish_iters):
                nb = self._neighbour(polish_current, violating_uids=None)
                nb_hard, nb_soft = self._penalty(nb, return_breakdown=True)
                if nb_hard == 0 and nb_soft < polish_soft:
                    polish_current, polish_soft = nb, nb_soft
            if polish_soft < best_soft:
                best, best_soft = polish_current, polish_soft
                if verbose:
                    print(f"  ✓ Polishing improved soft penalty: "
                          f"{best_soft} (was higher before)")

        return best, best_hard, best_soft


    def _print_violations(self, sol):
        def occupied(uid, s):
            return [s, s+1] if self.units[uid]["unit_type"] == "practical" else [s]

        slot_units = defaultdict(list)
        for uid, (s, r) in sol.items():
            for slot in occupied(uid, s):
                slot_units[slot].append(uid)

        h1 = h2 = h3 = h4 = h5 = 0
        for uid, (s, r) in sol.items():
            if self.units[uid]["unit_type"] == "practical" and not valid_practical_slot(s):
                h4 += 1
            is_prac = self.units[uid]["unit_type"] == "practical"
            if is_lunch_slot(s) or (is_prac and is_lunch_slot(s + 1)):
                h5 += 1

        for slot, uids in slot_units.items():
            n = len(uids)
            for i in range(n):
                for j in range(i+1, n):
                    if uids[j] in self.conflict_sets.get(uids[i], set()):
                        h1 += 1
            seen = set()
            for uid in uids:
                t = self.teacher_subjects.get(self.units[uid]["course_code"])
                if t:
                    if t in seen: h2 += 1
                    seen.add(t)
            seen = set()
            for uid in uids:
                r = sol[uid][1]
                if r in seen: h3 += 1
                seen.add(r)

        print(f"    H1 student clashes  : {h1}")
        print(f"    H2 teacher clashes  : {h2}")
        print(f"    H3 room clashes     : {h3}")
        print(f"    H4 practical at EOD : {h4}")
        print(f"    H5 lunch violations : {h5}")


def build_timetable_json(solution, data):
    subjects         = data["subjects"]
    units            = data["units"]
    rooms            = data["rooms"]
    teacher_subjects = data["teacher_subjects"]
    students         = data["students"]
    groups           = data["enrollment_groups"]
    day_order        = {d: i for i, d in enumerate(DAYS)}

    classes = []
    for uid, (start_slot, room_id) in solution.items():
        unit = units[uid]
        code = unit["course_code"]
        subj = subjects.get(code, {})
        room = rooms.get(room_id, {})
        slot1 = ALL_SLOTS[start_slot]

        if unit["unit_type"] == "practical":
            slot2    = ALL_SLOTS[start_slot + 1]
            end_time = slot2["end"]
            slots    = 2
        else:
            end_time = slot1["end"]
            slots    = 1

        classes.append({
            "unit_id":     uid,
            "course_code": code,
            "title":       subj.get("title", "") if isinstance(subj, dict) else subj.title,
            "credits":     subj.get("credits", 0) if isinstance(subj, dict) else subj.credits,
            "type":        unit["unit_type"],
            "slots":       slots,
            "day":         slot1["day"],
            "start":       slot1["start"],
            "end":         end_time,
            "slot_index":  start_slot,
            "room_id":     room_id,
            "room_type":   room.get("room_type", "") if isinstance(room, dict) else room.room_type,
            "capacity":    room.get("capacity", 0) if isinstance(room, dict) else room.capacity,
            "teacher":     teacher_subjects.get(code, "TBA"),
        })

    classes.sort(key=lambda c: (day_order[c["day"]], c["slot_index"]))
    by_day = {day: [c for c in classes if c["day"] == day] for day in DAYS}

    by_student = {}
    for enr, s in students.items():
        s_dict = s if isinstance(s, dict) else {
            "semester": s.semester, "major": s.major,
            "minor": s.minor, "name": s.name, "email": s.email
        }
        key     = f"sem{s_dict['semester']}|{s_dict['major']}|{s_dict['minor']}"
        my_uids = set(groups.get(key, []))
        my_cls  = [c for c in classes if c["unit_id"] in my_uids]

        by_student[enr] = {
            "enrollment_no": enr,
            "name":          s_dict["name"],
            "email":         s_dict["email"],
            "major":         s_dict["major"],
            "minor":         s_dict["minor"],
            "semester":      s_dict["semester"],
            "classes":       my_cls,
        }

    return {
        "meta": {
            "total_classes":         len(classes),
            "total_students":        len(by_student),
            "days":                  DAYS,
            "slots_per_day":         SLOTS_PER_DAY,
            "slot_duration_minutes": _SLOT_MINUTES,
            "timeslots":             ALL_SLOTS,
        },
        "timetable":  classes,
        "by_day":     by_day,
        "by_student": by_student,
    }


def run(extracted_json, output_json,
        initial_temp=10000.0, cooling_rate=0.995,
        min_temp=1.0, iters_per_temp=50, restart_threshold=500,
        max_steps=None, polish_iters=5000):

    print("=" * 65)
    print("  TSLAS TIMETABLE SCHEDULER  v3  —  Simulated Annealing")
    print("=" * 65)

    with open(extracted_json, encoding="utf-8") as f:
        raw = json.load(f)

    data = {
        "subjects":          raw["subjects"],
        "units":             raw["units"],
        "rooms":             raw["rooms"],
        "students":          raw["students"],
        "teacher_subjects":  raw["teacher_subjects"],
        "enrollment_groups": raw["enrollment_groups"],
        "conflict_graph":    {k: set(v) for k, v in raw["conflict_graph"].items()},
    }

    sched = TimetableScheduler(data)
    solution, hard_pen, soft_pen = sched.solve(
        initial_temp=initial_temp, cooling_rate=cooling_rate,
        min_temp=min_temp, iters_per_temp=iters_per_temp,
        restart_threshold=restart_threshold, max_steps=max_steps,
        polish_iters=polish_iters,
    )

    out = build_timetable_json(solution, data)

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\n  ✓ Timetable saved → {output_json}")
    print(f"  Class sessions : {out['meta']['total_classes']}")
    print(f"  Students       : {out['meta']['total_students']}")

    printed = 0
    for enr, s in out["by_student"].items():
        if s["classes"] and len(s["classes"]) >= 6:
            print(f"\n  ── {s['name']} ({enr})  sem{s['semester']}  {s['major']} + {s['minor']}")
            for c in s["classes"]:
                typ = {"lecture": "LEC", "tutorial": "TUT", "practical": "PRAC"}[c["type"]]
                print(f"     {c['day']:10s}  {c['start']}–{c['end']}  [{typ}]  "
                      f"{c['course_code']:10s}  {c['title'][:32]:32s}  "
                      f"[{c['room_id']:6s}]  {c['teacher'][:20]}")
            printed += 1
            if printed == 2: break
    return out