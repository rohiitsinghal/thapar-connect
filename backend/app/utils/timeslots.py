"""
Timeslot generation — NOT stored in the database.

We generate all valid (day, slot_index) pairs programmatically.
Each slot is 50 minutes.  The day runs 08:00 – 17:10, giving exactly 11 slots:

  Slot 0: 08:00 – 08:50
  Slot 1: 08:50 – 09:40
  ...
  Slot 10: 16:20 – 17:10

We use (day_index, slot_index) tuples throughout the solver to avoid any
database dependency in the hot path.  Day names are kept in DAYS for display.
"""

from dataclasses import dataclass
from typing import List, Tuple

# Days of the teaching week, indexed 0–4
DAYS: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Day start time in minutes from midnight
DAY_START_MINUTES: int = 8 * 60        # 08:00

# Each lecture lasts 50 minutes
LECTURE_DURATION: int = 50

# How many lectures fit between 08:00 and 17:10
# 17:10 = 17*60+10 = 1030 minutes; 08:00 = 480 minutes; range = 550 min
# 550 / 50 = 11 slots exactly
SLOTS_PER_DAY: int = 11


@dataclass(frozen=True)
class Timeslot:
    """Immutable value object representing one lecture slot."""
    day_index: int      # 0 = Monday … 4 = Friday
    slot_index: int     # 0 = 08:00 … 10 = 16:20

    @property
    def day_name(self) -> str:
        return DAYS[self.day_index]

    @property
    def start_time(self) -> str:
        """Human-readable start time, e.g. '09:40'."""
        total = DAY_START_MINUTES + self.slot_index * LECTURE_DURATION
        h, m = divmod(total, 60)
        return f"{h:02d}:{m:02d}"

    @property
    def end_time(self) -> str:
        """Human-readable end time."""
        total = DAY_START_MINUTES + (self.slot_index + 1) * LECTURE_DURATION
        h, m = divmod(total, 60)
        return f"{h:02d}:{m:02d}"

    def __repr__(self) -> str:
        return f"{self.day_name} {self.start_time}-{self.end_time}"


def generate_all_timeslots() -> List[Timeslot]:
    """
    Returns all 55 timeslots (5 days × 11 slots) as a flat list.
    Order: Monday slot-0 … Monday slot-10, Tuesday slot-0 … Friday slot-10.
    """
    return [
        Timeslot(day_index=d, slot_index=s)
        for d in range(len(DAYS))
        for s in range(SLOTS_PER_DAY)
    ]


# Pre-built lookup: (day_index, slot_index) → Timeslot object
TIMESLOT_MAP: dict[Tuple[int, int], Timeslot] = {
    (ts.day_index, ts.slot_index): ts
    for ts in generate_all_timeslots()
}

ALL_TIMESLOTS: List[Timeslot] = generate_all_timeslots()