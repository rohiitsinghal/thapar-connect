"""
Constraint-based timetable solver — semester-aware.

The only change from the previous version: `run_solver` now accepts a
`semester` integer and filters subjects to only those belonging to that
semester.  The SA algorithm, move types, hard constraints, and penalty
functions are all unchanged.

Call pattern:
    placements, score = run_solver(db, semester=1)
    placements, score = run_solver(db, semester=2)
    ...
    placements, score = run_solver(db, semester=8)

Each call is fully independent — it schedules only the subjects for that
semester.  Rooms are shared across all batches within the semester but not
across semesters (each semester is a separate scheduling problem).
"""

import math
import random
import logging
from dataclasses import dataclass, field
from typing      import List, Dict, Set, Tuple, Optional

from sqlalchemy.orm import Session

from app.models.models    import Teacher, Room, Batch, Subject, TimetableEntry
from app.utils.timeslots  import ALL_TIMESLOTS, Timeslot
from app.services.scoring import Placement, compute_penalty
from app.core.config      import settings

logger = logging.getLogger(__name__)


# ── Solver state ──────────────────────────────────────────────────────────────

@dataclass
class SolverState:
    placements:   List[Placement] = field(default_factory=list)
    teacher_busy: Set[Tuple]      = field(default_factory=set)
    room_busy:    Set[Tuple]      = field(default_factory=set)
    batch_busy:   Set[Tuple]      = field(default_factory=set)


# ── Hard-constraint helpers ───────────────────────────────────────────────────

def _is_valid_placement(
    state: SolverState,
    teacher_id: int, room_id: int, batch_id: int,
    day: int, slot: int,
    room_capacity: int, batch_size: int,
) -> bool:
    if room_capacity < batch_size:
        return False
    if (teacher_id, day, slot) in state.teacher_busy:
        return False
    if (room_id,    day, slot) in state.room_busy:
        return False
    if (batch_id,   day, slot) in state.batch_busy:
        return False
    return True


def _add_placement(state: SolverState, p: Placement) -> None:
    state.placements.append(p)
    state.teacher_busy.add((p.teacher_id, p.day, p.slot))
    state.room_busy.add((p.room_id,       p.day, p.slot))
    state.batch_busy.add((p.batch_id,     p.day, p.slot))


def _remove_placement(state: SolverState, p: Placement) -> None:
    state.placements.remove(p)
    state.teacher_busy.discard((p.teacher_id, p.day, p.slot))
    state.room_busy.discard((p.room_id,       p.day, p.slot))
    state.batch_busy.discard((p.batch_id,     p.day, p.slot))


# ── Phase 3 — Initial random assignment ──────────────────────────────────────

def _build_initial_assignment(
    subjects:    List[Subject],
    rooms:       List[Room],
    timeslots:   List[Timeslot],
    max_retries: int,
) -> Optional[SolverState]:
    tasks: List[Subject] = []
    for subject in subjects:
        for _ in range(subject.lectures_per_week):
            tasks.append(subject)

    for attempt in range(max_retries):
        state         = SolverState()
        subject_days: Dict[int, Set[int]] = {}
        random.shuffle(tasks)
        success = True

        for subject in tasks:
            batch      = subject.batch
            teacher_id = subject.teacher_id
            batch_id   = subject.batch_id
            batch_size = batch.size
            used_days  = subject_days.get(subject.id, set())

            ts_candidates   = timeslots[:]
            room_candidates = rooms[:]
            random.shuffle(ts_candidates)
            random.shuffle(room_candidates)

            placed = False
            for ts in ts_candidates:
                if ts.day_index in used_days:
                    continue
                for room in room_candidates:
                    if _is_valid_placement(
                        state,
                        teacher_id=teacher_id, room_id=room.id,
                        batch_id=batch_id,
                        day=ts.day_index, slot=ts.slot_index,
                        room_capacity=room.capacity, batch_size=batch_size,
                    ):
                        _add_placement(state, Placement(
                            subject_id=subject.id, teacher_id=teacher_id,
                            batch_id=batch_id,     room_id=room.id,
                            day=ts.day_index,      slot=ts.slot_index,
                        ))
                        subject_days.setdefault(subject.id, set()).add(ts.day_index)
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                logger.warning(
                    f"Attempt {attempt+1}: could not place "
                    f"subject {subject.id} ('{subject.name}'). Retrying."
                )
                success = False
                break

        if success:
            logger.info(f"Initial assignment succeeded on attempt {attempt+1}.")
            return state

    return None


# ── SA helpers ────────────────────────────────────────────────────────────────

def _sa_accept(delta: int, temperature: float) -> bool:
    if delta < 0:
        return True
    if temperature < 1e-6:
        return False
    return random.random() < math.exp(-delta / temperature)


def _subject_days(state: SolverState, subject_id: int, exclude: Placement) -> Set[int]:
    return {q.day for q in state.placements
            if q.subject_id == subject_id and q is not exclude}


# ── Phase 5 — One SA move ─────────────────────────────────────────────────────

def _try_move_placement(
    state:       SolverState,
    rooms:       List[Room],
    timeslots:   List[Timeslot],
    room_map:    Dict[int, Room],
    batch_map:   Dict[int, Batch],
    temperature: float,
) -> bool:
    if not state.placements:
        return False

    p             = random.choice(state.placements)
    batch         = batch_map[p.batch_id]
    current_score = compute_penalty(state.placements)
    other_days    = _subject_days(state, p.subject_id, exclude=p)

    # ── Move 1: new timeslot, same room ──────────────────────────────────
    candidate_slots = [
        ts for ts in timeslots
        if not (ts.day_index == p.day and ts.slot_index == p.slot)
        and ts.day_index not in other_days
    ]
    random.shuffle(candidate_slots)

    room = room_map[p.room_id]
    _remove_placement(state, p)

    for ts in candidate_slots:
        if _is_valid_placement(
            state, p.teacher_id, p.room_id, p.batch_id,
            ts.day_index, ts.slot_index, room.capacity, batch.size,
        ):
            new_p = Placement(
                p.subject_id, p.teacher_id, p.batch_id, p.room_id,
                ts.day_index, ts.slot_index,
            )
            _add_placement(state, new_p)
            if _sa_accept(compute_penalty(state.placements) - current_score, temperature):
                return True
            _remove_placement(state, new_p)

    _add_placement(state, p)

    # ── Move 2: new room, same timeslot ──────────────────────────────────
    candidate_rooms = [r for r in rooms if r.id != p.room_id and r.capacity >= batch.size]
    random.shuffle(candidate_rooms)
    _remove_placement(state, p)

    for room in candidate_rooms:
        if _is_valid_placement(
            state, p.teacher_id, room.id, p.batch_id,
            p.day, p.slot, room.capacity, batch.size,
        ):
            new_p = Placement(
                p.subject_id, p.teacher_id, p.batch_id, room.id,
                p.day, p.slot,
            )
            _add_placement(state, new_p)
            if _sa_accept(compute_penalty(state.placements) - current_score, temperature):
                return True
            _remove_placement(state, new_p)

    _add_placement(state, p)

    # ── Move 3: swap timeslots with another placement ─────────────────────
    if len(state.placements) >= 2:
        other       = random.choice([x for x in state.placements if x is not p])
        other_batch = batch_map[other.batch_id]

        p_days_after     = _subject_days(state, p.subject_id,     exclude=p)
        other_days_after = _subject_days(state, other.subject_id, exclude=other)

        if other.day in p_days_after or p.day in other_days_after:
            return False

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
            sp = Placement(p.subject_id,     p.teacher_id,     p.batch_id,     p.room_id,     other.day, other.slot)
            so = Placement(other.subject_id, other.teacher_id, other.batch_id, other.room_id, p.day,     p.slot)
            _add_placement(state, sp)
            _add_placement(state, so)
            if _sa_accept(compute_penalty(state.placements) - current_score, temperature):
                return True
            _remove_placement(state, sp)
            _remove_placement(state, so)

        _add_placement(state, p)
        _add_placement(state, other)

    return False


# ── Public entry point ────────────────────────────────────────────────────────

def run_solver(db: Session, semester: int) -> Tuple[List[Placement], int]:
    """
    Schedule all subjects for `semester` and return (placements, penalty).

    Only subjects whose Subject.semester == semester are loaded.
    Rooms and teachers are loaded in full (they are shared infrastructure).
    """
    # ── Load data filtered to this semester ──────────────────────────────
    subjects = db.query(Subject).filter(Subject.semester == semester).all()
    rooms    = db.query(Room).all()
    batches  = db.query(Batch).all()

    if not subjects:
        raise ValueError(
            f"No subjects found for semester {semester}. "
            f"Run the seed script first."
        )

    room_map:  Dict[int, Room]  = {r.id: r for r in rooms}
    batch_map: Dict[int, Batch] = {b.id: b for b in batches}

    logger.info(
        f"Solver: semester={semester}, "
        f"subjects={len(subjects)}, rooms={len(rooms)}, batches={len(batches)}"
    )

    # ── Phase 3: initial assignment ───────────────────────────────────────
    state = _build_initial_assignment(
        subjects    = subjects,
        rooms       = rooms,
        timeslots   = ALL_TIMESLOTS,
        max_retries = settings.SOLVER_MAX_RETRIES,
    )
    if state is None:
        raise RuntimeError(
            f"Solver failed to find a valid initial assignment for semester {semester}. "
            f"Add more rooms or reduce subjects per batch."
        )

    # ── Phase 4: score ────────────────────────────────────────────────────
    best_score      = compute_penalty(state.placements)
    best_placements = list(state.placements)
    logger.info(f"Semester {semester} initial penalty: {best_score}")

    # ── Phase 5: Simulated Annealing ──────────────────────────────────────
    iterations   = settings.SOLVER_ITERATIONS
    T_START      = settings.SA_T_START
    T_END        = settings.SA_T_END
    cooling_rate = (T_END / T_START) ** (1.0 / max(iterations, 1))
    temperature  = T_START

    for i in range(iterations):
        _try_move_placement(state, rooms, ALL_TIMESLOTS, room_map, batch_map, temperature)

        score = compute_penalty(state.placements)
        if score < best_score:
            best_score      = score
            best_placements = list(state.placements)
            logger.debug(f"Sem {semester} iter {i:>6} T={temperature:7.2f} best={best_score}")

        temperature *= cooling_rate

        if best_score == 0:
            logger.info(f"Semester {semester}: perfect score at iter {i}.")
            break

    logger.info(
        f"Semester {semester} done. "
        f"Best penalty={best_score} | Final T={temperature:.4f}"
    )
    return best_placements, best_score