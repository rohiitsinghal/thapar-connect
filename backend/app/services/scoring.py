"""
Soft-constraint scoring system.

A timetable is represented as a list of Placement objects (in-memory).
The scorer walks the placements and accumulates a penalty score.

LOWER SCORE = BETTER TIMETABLE (like a cost function in optimisation).

Penalties:
  +10  per person/batch with >4 consecutive lectures in a day
  +5   per day where a teacher's lecture count deviates from their daily average
  +3   per gap of ≥2 free slots between two lectures in a batch's day
  +2   per day where a batch has more lectures than adjacent days (clustering)

Design choice — why a penalty (minimisation) instead of a reward (maximisation):
  Easier to reason about: zero means "perfect soft constraint satisfaction".
  Local search clearly knows it is improving when the score decreases.
"""

from dataclasses import dataclass
from collections import defaultdict
from typing import List

from app.utils.timeslots import SLOTS_PER_DAY, DAYS


@dataclass
class Placement:
    """
    In-memory representation of one scheduled lecture.
    Mirrors TimetableEntry but is a plain Python object — no ORM overhead.
    """
    subject_id: int
    teacher_id: int
    batch_id:   int
    room_id:    int
    day:        int     # 0–4
    slot:       int     # 0–10


# ---------------------------------------------------------------------------
# Individual penalty functions
# ---------------------------------------------------------------------------

def _consecutive_penalty(placements: List[Placement]) -> int:
    """
    Penalty for >4 consecutive occupied slots for a teacher or batch.

    We build a set of (entity_id, day, slot) and then for each (entity, day)
    combination count the longest run of consecutive slots.
    Penalty = 10 × (run_length - 4) for each run > 4.
    """
    penalty = 0

    # Build slot sets keyed by (entity_id, day)
    teacher_slots: dict = defaultdict(set)
    batch_slots:   dict = defaultdict(set)

    for p in placements:
        teacher_slots[(p.teacher_id, p.day)].add(p.slot)
        batch_slots[(p.batch_id, p.day)].add(p.slot)

    def max_run(slot_set: set) -> int:
        """Length of the longest consecutive run in a set of slot indices."""
        if not slot_set:
            return 0
        sorted_slots = sorted(slot_set)
        max_len = cur_len = 1
        for i in range(1, len(sorted_slots)):
            if sorted_slots[i] == sorted_slots[i - 1] + 1:
                cur_len += 1
                max_len = max(max_len, cur_len)
            else:
                cur_len = 1
        return max_len

    for slot_set in teacher_slots.values():
        run = max_run(slot_set)
        if run > 4:
            penalty += 10 * (run - 4)

    for slot_set in batch_slots.values():
        run = max_run(slot_set)
        if run > 4:
            penalty += 10 * (run - 4)

    return penalty


def _teacher_balance_penalty(placements: List[Placement]) -> int:
    """
    Penalty for uneven daily workload distribution per teacher.

    For each teacher, compute their total lectures and ideal daily load
    (total / 5 days).  Penalise each day that deviates by more than 1.

    Penalty = 5 × abs(daily_count - ideal) for each day where deviation > 1.
    """
    penalty = 0

    # teacher_id → day → count
    teacher_day: dict = defaultdict(lambda: defaultdict(int))
    for p in placements:
        teacher_day[p.teacher_id][p.day] += 1

    for t_id, day_counts in teacher_day.items():
        total = sum(day_counts.values())
        ideal = total / len(DAYS)           # float daily average
        for d in range(len(DAYS)):
            daily = day_counts.get(d, 0)
            deviation = abs(daily - ideal)
            if deviation > 1:
                penalty += 5 * int(deviation)

    return penalty


def _batch_gap_penalty(placements: List[Placement]) -> int:
    """
    Penalty for large gaps in a batch's day.

    A gap = two or more consecutive free slots sandwiched between occupied
    slots.  Each such gap adds 3 to the penalty.

    Example: batch has lectures at slots 1, 4 → gap of 2 free slots → +3.
    """
    penalty = 0

    batch_slots: dict = defaultdict(lambda: defaultdict(list))
    for p in placements:
        batch_slots[p.batch_id][p.day].append(p.slot)

    for b_id, days in batch_slots.items():
        for day, slots in days.items():
            if len(slots) < 2:
                continue
            sorted_slots = sorted(slots)
            for i in range(len(sorted_slots) - 1):
                gap = sorted_slots[i + 1] - sorted_slots[i] - 1
                if gap >= 2:
                    penalty += 3

    return penalty


def _clustering_penalty(placements: List[Placement]) -> int:
    """
    Penalty for clustering a batch's lectures on few days.

    Ideal: lectures spread as evenly as possible across the week.
    We measure the standard-deviation-like spread: sum of squared deviations
    from the mean.  Scaled by 2.
    """
    penalty = 0

    batch_day: dict = defaultdict(lambda: defaultdict(int))
    for p in placements:
        batch_day[p.batch_id][p.day] += 1

    for b_id, day_counts in batch_day.items():
        total = sum(day_counts.values())
        mean  = total / len(DAYS)
        for d in range(len(DAYS)):
            diff = abs(day_counts.get(d, 0) - mean)
            if diff > 1:
                penalty += 2 * int(diff)

    return penalty


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_penalty(placements: List[Placement]) -> int:
    """
    Compute the total soft-constraint penalty for a list of placements.

    Returns an integer ≥ 0.  Zero means all soft constraints are satisfied.
    """
    return (
        _consecutive_penalty(placements)
        + _teacher_balance_penalty(placements)
        + _batch_gap_penalty(placements)
        + _clustering_penalty(placements)
    )