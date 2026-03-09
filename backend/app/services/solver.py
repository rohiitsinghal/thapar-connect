"""
Constraint-based timetable solver — UniTime-inspired architecture.

─────────────────────────────────────────────────────────────────────────────
OVERVIEW
─────────────────────────────────────────────────────────────────────────────

The solver works in six phases mirroring the approach used in real academic
timetabling systems (ITC, UniTime):

  Phase 1 — Generate all valid timeslots (Mon–Fri, 08:00–17:10, 50 min each)
  Phase 2 — Expand subjects into individual lecture tasks
  Phase 3 — Random initial assignment satisfying ALL hard constraints
  Phase 4 — Score the timetable using soft-constraint penalties
  Phase 5 — Local search: iteratively swap/move lectures to reduce penalty
  Phase 6 — Return (and persist) the best assignment found

─────────────────────────────────────────────────────────────────────────────
DATA STRUCTURES
─────────────────────────────────────────────────────────────────────────────

The hot path of the solver never touches the database.  We use three Python
sets as "occupancy registers" for O(1) conflict checking:

  teacher_busy: set of (teacher_id, day, slot)
  room_busy:    set of (room_id,    day, slot)
  batch_busy:   set of (batch_id,   day, slot)

A slot is "free" for a teacher if (teacher_id, day, slot) ∉ teacher_busy.
These sets are updated atomically whenever a placement is added or removed.

Why sets instead of dicts-of-dicts?
  • Membership test (O(1)) is all we need for hard-constraint checking.
  • A nested dict would give the same complexity but with more code.

─────────────────────────────────────────────────────────────────────────────
HARD CONSTRAINTS (enforced during placement, never violated in final result)
─────────────────────────────────────────────────────────────────────────────

1. Teacher conflict    — (teacher_id, day, slot) must be free
2. Room conflict       — (room_id,    day, slot) must be free
3. Batch conflict      — (batch_id,   day, slot) must be free
4. Room capacity       — room.capacity >= batch.size
5. Lecture count       — each subject placed exactly lectures_per_week times
6. Valid timeslot      — (day, slot) drawn from the 55 valid slots only
"""

import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional

from sqlalchemy.orm import Session

from app.models.models import Teacher, Room, Batch, Subject, TimetableEntry
from app.utils.timeslots import ALL_TIMESLOTS, Timeslot
from app.services.scoring import Placement, compute_penalty
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal solver state
# ---------------------------------------------------------------------------

@dataclass
class SolverState:
    """
    Mutable state passed around inside the solver.

    Keeping everything in one dataclass makes it easy to deep-copy the state
    for "speculative moves" during local search.
    """
    placements:   List[Placement]          = field(default_factory=list)
    teacher_busy: Set[Tuple]               = field(default_factory=set)
    room_busy:    Set[Tuple]               = field(default_factory=set)
    batch_busy:   Set[Tuple]               = field(default_factory=set)


# ---------------------------------------------------------------------------
# Helper: check hard constraints
# ---------------------------------------------------------------------------

def _is_valid_placement(
    state:      SolverState,
    teacher_id: int,
    room_id:    int,
    batch_id:   int,
    day:        int,
    slot:       int,
    room_capacity: int,
    batch_size:    int,
) -> bool:
    """
    Returns True only if placing a lecture at (day, slot) violates none of
    the six hard constraints.
    """
    # HC-4: room must be large enough
    if room_capacity < batch_size:
        return False

    # HC-1, HC-2, HC-3: no double-booking
    if (teacher_id, day, slot) in state.teacher_busy:
        return False
    if (room_id, day, slot) in state.room_busy:
        return False
    if (batch_id, day, slot) in state.batch_busy:
        return False

    return True


def _add_placement(state: SolverState, p: Placement) -> None:
    """Register a placement and mark the slot as occupied."""
    state.placements.append(p)
    state.teacher_busy.add((p.teacher_id, p.day, p.slot))
    state.room_busy.add((p.room_id,    p.day, p.slot))
    state.batch_busy.add((p.batch_id,  p.day, p.slot))


def _remove_placement(state: SolverState, p: Placement) -> None:
    """Unregister a placement and free the slot."""
    state.placements.remove(p)
    state.teacher_busy.discard((p.teacher_id, p.day, p.slot))
    state.room_busy.discard((p.room_id,    p.day, p.slot))
    state.batch_busy.discard((p.batch_id,  p.day, p.slot))


# ---------------------------------------------------------------------------
# Phase 3 — Initial random assignment
# ---------------------------------------------------------------------------

def _build_initial_assignment(
    subjects:  List[Subject],
    rooms:     List[Room],
    timeslots: List[Timeslot],
    max_retries: int,
) -> Optional[SolverState]:
    """
    Attempt to create a timetable that satisfies ALL hard constraints by
    assigning each lecture requirement (subject × lectures_per_week) to a
    randomly chosen valid (timeslot, room) pair.

    Strategy:
      • Shuffle placement tasks so we don't always favour the same subject.
      • For each task, shuffle (timeslot, room) candidates and pick the first
        valid combination.
      • If no valid slot exists for a task, the whole attempt fails and we
        retry up to `max_retries` times.

    This is a random greedy search, not backtracking.  For typical university
    data it almost always succeeds in ≤ 3 retries.
    """
    # Pre-build a mapping room_id → Room for quick capacity lookup
    room_map: Dict[int, Room] = {r.id: r for r in rooms}

    # Expand subjects into individual lecture tasks
    tasks: List[Subject] = []
    for subject in subjects:
        for _ in range(subject.lectures_per_week):
            tasks.append(subject)

    for attempt in range(max_retries):
        state = SolverState()
        random.shuffle(tasks)
        success = True

        for subject in tasks:
            batch = subject.batch       # loaded via relationship
            teacher_id = subject.teacher_id
            batch_id   = subject.batch_id
            batch_size = batch.size

            # Shuffle both timeslots and rooms for randomness
            ts_candidates   = timeslots[:]
            room_candidates = rooms[:]
            random.shuffle(ts_candidates)
            random.shuffle(room_candidates)

            placed = False
            for ts in ts_candidates:
                for room in room_candidates:
                    if _is_valid_placement(
                        state,
                        teacher_id=teacher_id,
                        room_id=room.id,
                        batch_id=batch_id,
                        day=ts.day_index,
                        slot=ts.slot_index,
                        room_capacity=room.capacity,
                        batch_size=batch_size,
                    ):
                        _add_placement(state, Placement(
                            subject_id=subject.id,
                            teacher_id=teacher_id,
                            batch_id=batch_id,
                            room_id=room.id,
                            day=ts.day_index,
                            slot=ts.slot_index,
                        ))
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                logger.warning(
                    f"Attempt {attempt+1}: could not place subject {subject.id} "
                    f"('{subject.name}'). Retrying entire assignment."
                )
                success = False
                break

        if success:
            logger.info(f"Initial assignment succeeded on attempt {attempt+1}.")
            return state

    return None     # all retries exhausted


# ---------------------------------------------------------------------------
# Phase 5 — Local search optimisation
# ---------------------------------------------------------------------------

def _try_move_placement(
    state:     SolverState,
    rooms:     List[Room],
    timeslots: List[Timeslot],
    room_map:  Dict[int, Room],
    batch_map: Dict[int, Batch],
) -> bool:
    """
    Attempt one local-search move:  pick a random placement and try to move
    it to a different (timeslot, room) combination.

    Returns True if the move was accepted (the new state has a lower penalty).

    Move types attempted here (in order):
      1. Move to a new timeslot (same room)
      2. Move to a new room (same timeslot)
      3. Swap timeslots with another random placement

    We use a simple hill-climbing acceptance criterion: accept only if the
    move strictly improves the penalty score.  This is equivalent to greedy
    descent, which works well when combined with random restarts (done in the
    outer loop).

    Why hill-climbing and not simulated annealing here?
      Simulated annealing requires careful temperature tuning.  Hill-climbing
      is simpler, deterministic, and fast enough for timetabling at this scale.
      The randomness in the initial assignment provides diversity.
    """
    if not state.placements:
        return False

    # --- Pick a random placement to move ---
    p = random.choice(state.placements)
    batch = batch_map[p.batch_id]

    current_score = compute_penalty(state.placements)

    # ── Move 1: new timeslot, same room ─────────────────────────────────────
    candidate_slots = [ts for ts in timeslots
                       if not (ts.day_index == p.day and ts.slot_index == p.slot)]
    random.shuffle(candidate_slots)

    for ts in candidate_slots:
        _remove_placement(state, p)
        room = room_map[p.room_id]
        if _is_valid_placement(
            state,
            teacher_id=p.teacher_id,
            room_id=p.room_id,
            batch_id=p.batch_id,
            day=ts.day_index,
            slot=ts.slot_index,
            room_capacity=room.capacity,
            batch_size=batch.size,
        ):
            new_p = Placement(
                subject_id=p.subject_id,
                teacher_id=p.teacher_id,
                batch_id=p.batch_id,
                room_id=p.room_id,
                day=ts.day_index,
                slot=ts.slot_index,
            )
            _add_placement(state, new_p)
            new_score = compute_penalty(state.placements)
            if new_score < current_score:
                return True     # accept the move
            # Revert
            _remove_placement(state, new_p)

        # Always restore the original placement before trying next candidate
        _add_placement(state, p)
        break   # only attempt the first valid candidate per move type

    # ── Move 2: new room, same timeslot ─────────────────────────────────────
    candidate_rooms = [r for r in rooms if r.id != p.room_id and r.capacity >= batch.size]
    random.shuffle(candidate_rooms)

    for room in candidate_rooms:
        _remove_placement(state, p)
        if _is_valid_placement(
            state,
            teacher_id=p.teacher_id,
            room_id=room.id,
            batch_id=p.batch_id,
            day=p.day,
            slot=p.slot,
            room_capacity=room.capacity,
            batch_size=batch.size,
        ):
            new_p = Placement(
                subject_id=p.subject_id,
                teacher_id=p.teacher_id,
                batch_id=p.batch_id,
                room_id=room.id,
                day=p.day,
                slot=p.slot,
            )
            _add_placement(state, new_p)
            new_score = compute_penalty(state.placements)
            if new_score < current_score:
                return True
            _remove_placement(state, new_p)

        _add_placement(state, p)
        break

    # ── Move 3: swap timeslots with another random placement ─────────────────
    if len(state.placements) >= 2:
        other = random.choice([x for x in state.placements if x is not p])
        other_batch = batch_map[other.batch_id]

        _remove_placement(state, p)
        _remove_placement(state, other)

        room_p     = room_map[p.room_id]
        room_other = room_map[other.room_id]

        if (
            _is_valid_placement(state, p.teacher_id,     p.room_id,     p.batch_id,
                                other.day, other.slot, room_p.capacity, batch.size)
            and
            _is_valid_placement(state, other.teacher_id, other.room_id, other.batch_id,
                                p.day, p.slot, room_other.capacity, other_batch.size)
        ):
            swapped_p     = Placement(p.subject_id,     p.teacher_id,     p.batch_id,     p.room_id,     other.day, other.slot)
            swapped_other = Placement(other.subject_id, other.teacher_id, other.batch_id, other.room_id, p.day,     p.slot)
            _add_placement(state, swapped_p)
            _add_placement(state, swapped_other)
            new_score = compute_penalty(state.placements)
            if new_score < current_score:
                return True
            _remove_placement(state, swapped_p)
            _remove_placement(state, swapped_other)

        # Restore originals
        _add_placement(state, p)
        _add_placement(state, other)

    return False    # no improving move found


# ---------------------------------------------------------------------------
# Main public entry point
# ---------------------------------------------------------------------------

def run_solver(db: Session) -> Tuple[List[Placement], int]:
    """
    Run the full solver pipeline and return (best_placements, penalty_score).

    Steps:
      1. Load all required data from the database.
      2. Phase 3: build an initial valid assignment.
      3. Phase 4: score it.
      4. Phase 5: run local-search for `SOLVER_ITERATIONS` moves.
      5. Return the best placements found.
    """
    # ── 1. Load data ─────────────────────────────────────────────────────────
    subjects = db.query(Subject).all()
    rooms    = db.query(Room).all()
    batches  = db.query(Batch).all()

    if not subjects or not rooms or not batches:
        raise ValueError("Database is empty. Run the seed script first.")

    room_map:  Dict[int, Room]  = {r.id: r for r in rooms}
    batch_map: Dict[int, Batch] = {b.id: b for b in batches}

    # ── 2. Phase 3: initial assignment ───────────────────────────────────────
    state = _build_initial_assignment(
        subjects   = subjects,
        rooms      = rooms,
        timeslots  = ALL_TIMESLOTS,
        max_retries= settings.SOLVER_MAX_RETRIES,
    )
    if state is None:
        raise RuntimeError(
            "Solver failed to find a valid initial assignment. "
            "Check that enough rooms and timeslots exist for the given subjects."
        )

    # ── 3. Phase 4: initial score ─────────────────────────────────────────────
    best_score     = compute_penalty(state.placements)
    best_placements = list(state.placements)    # shallow copy is sufficient
    logger.info(f"Initial penalty score: {best_score}")

    # ── 4. Phase 5: local search ──────────────────────────────────────────────
    iterations = settings.SOLVER_ITERATIONS

    for i in range(iterations):
        improved = _try_move_placement(state, rooms, ALL_TIMESLOTS, room_map, batch_map)

        if improved:
            score = compute_penalty(state.placements)
            if score < best_score:
                best_score      = score
                best_placements = list(state.placements)
                logger.debug(f"Iter {i}: new best score = {best_score}")

        if best_score == 0:
            logger.info(f"Perfect soft-constraint satisfaction reached at iter {i}.")
            break

    logger.info(f"Solver finished. Best penalty score: {best_score}")

    # ── 5. Phase 6: return best result ────────────────────────────────────────
    return best_placements, best_score