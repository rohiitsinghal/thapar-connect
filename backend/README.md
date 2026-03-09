# University Timetable Scheduling System

A constraint-based timetable generator inspired by **UniTime**, built with Python, FastAPI, PostgreSQL, and SQLAlchemy.

This is not a simple greedy scheduler. It implements a full **local-search optimisation** pipeline with hard-constraint enforcement and soft-constraint penalty scoring.

---

## Architecture Overview

```
app/
├── main.py                   # FastAPI app, startup hooks, router registration
├── core/
│   ├── config.py             # Pydantic Settings (env vars, solver params)
│   └── database.py           # SQLAlchemy engine + session factory
├── models/
│   └── models.py             # ORM models: Teacher, Room, Batch, Subject, TimetableEntry
├── schemas/
│   └── schemas.py            # Pydantic request/response schemas
├── services/
│   ├── solver.py             # Main solver pipeline (phases 1–6)
│   ├── scoring.py            # Soft-constraint penalty functions
│   └── optimizer.py          # Persistence + response building
├── api/routes/
│   └── timetable.py          # FastAPI route handlers
├── utils/
│   └── timeslots.py          # Programmatic timeslot generation (not stored in DB)
└── seed/
    └── seed_data.py          # Test data: 10 teachers, 10 rooms, 4 batches, 20 subjects
```

---

## Algorithm

### Week Structure
- **Days:** Monday–Friday (5 days)
- **Hours:** 08:00–17:10
- **Duration:** 50 minutes per lecture
- **Slots per day:** 11 (08:00, 08:50, 09:40, … 16:20)
- **Total slots per week:** 55

### Solver Pipeline

#### Phase 1 — Timeslot Generation
All 55 timeslots are generated programmatically in `utils/timeslots.py`. They are **never stored in the database** — this avoids a lookup table that would only ever be read, never mutated.

#### Phase 2 — Lecture Task Expansion
Each `Subject` with `lectures_per_week = N` is expanded into `N` individual placement tasks. A subject requiring 3 lectures produces 3 tasks.

#### Phase 3 — Initial Random Assignment (Hard Constraint Satisfaction)
A random greedy search assigns each task to a (timeslot, room) pair that violates none of the 6 hard constraints:

| # | Hard Constraint |
|---|----------------|
| 1 | Teacher cannot be in two places at once |
| 2 | Room cannot host two classes at once |
| 3 | Batch cannot attend two classes at once |
| 4 | Room capacity ≥ batch size |
| 5 | Each subject scheduled exactly `lectures_per_week` times |
| 6 | All slots within Mon–Fri 08:00–17:10 |

**Data structures for O(1) conflict checking:**
```python
teacher_busy: set  # of (teacher_id, day, slot)
room_busy:    set  # of (room_id,    day, slot)
batch_busy:   set  # of (batch_id,   day, slot)
```

Why sets? Membership check is O(1) on average, which is critical when evaluating thousands of candidate moves per second.

#### Phase 4 — Penalty Scoring
The timetable is scored by accumulating penalties for soft-constraint violations:

| Penalty | Soft Constraint |
|---------|----------------|
| +10 × excess | Teacher or batch has >4 consecutive lectures |
| +5 × deviation | Teacher's daily load deviates from weekly average |
| +3 per gap | Batch has ≥2 free slots between two lectures in the same day |
| +2 × deviation | Batch lectures clustered on fewer days than average |

**Score = 0 means all soft constraints are perfectly satisfied.** Lower is better.

#### Phase 5 — Local Search Optimisation
Iteratively improves the timetable. On each iteration:
1. Pick a random placement
2. Try three move types:
   - **Move to new timeslot** (same room)
   - **Move to new room** (same timeslot)
   - **Swap timeslots with another placement**
3. Accept the move only if it **reduces the penalty score** (greedy hill-climbing)
4. Track the best solution seen

This repeats for `SOLVER_ITERATIONS` (default: 1000) iterations.

#### Phase 6 — Persist and Return
The best-scoring timetable is saved to PostgreSQL and returned to the caller.

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- (Recommended) a virtual environment

---

## Setup Instructions

### 1. Clone and enter the project
```bash
git clone <repo>
cd timetable_system
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure the database
```bash
cp .env.example .env
# Edit .env and set DATABASE_URL to your PostgreSQL connection string
```

Default: `postgresql://postgres:postgres@localhost:5432/timetable_db`

Create the database:
```sql
CREATE DATABASE timetable_db;
```

### 5. Seed the database
```bash
python -m app.seed.seed_data
```

This creates 10 teachers, 10 rooms, 4 batches, and 20 subjects (47 total lecture slots to schedule).

### 6. Start the server
```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

---

## API Usage

### Generate a timetable
```bash
curl -X POST http://localhost:8000/generate-timetable \
     -H "Content-Type: application/json" \
     -d '{"iterations": 1000}'
```

Response:
```json
{
  "message": "Timetable generated and saved successfully.",
  "total_entries": 47,
  "penalty_score": 12
}
```

### Get a batch timetable
```bash
curl http://localhost:8000/batch/1/timetable
```

### Get a teacher timetable
```bash
curl http://localhost:8000/teacher/1/timetable
```

### Get a room timetable
```bash
curl http://localhost:8000/room/1/timetable
```

Each entry in the response looks like:
```json
{
  "id": 1,
  "day": 0,
  "slot_index": 2,
  "day_name": "Monday",
  "start_time": "09:40",
  "end_time": "10:30",
  "teacher_id": 1,
  "teacher_name": "Dr. Alice Mercer",
  "room_id": 3,
  "room_name": "LH-103",
  "batch_id": 1,
  "batch_name": "CS-Year1-A",
  "subject_id": 1,
  "subject_name": "Introduction to Programming"
}
```

---

## Tuning the Solver

Edit `.env` or pass `iterations` in the POST body:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `SOLVER_ITERATIONS` | 1000 | More iterations = lower penalty score but slower |
| `SOLVER_MAX_RETRIES` | 5 | Retries for initial random assignment |

---

## Running Tests (optional, if you add pytest)

```bash
pytest tests/
```

---

## Design Decisions

**Why not store timeslots in the database?**  
Timeslots are a fixed, purely computational concept. Storing them would create a read-only lookup table that never changes. Generating them programmatically is simpler and faster.

**Why plain sets for occupancy tracking?**  
Set membership (`__contains__`) is O(1) average vs O(n) for list scan. With 1000+ local-search iterations each checking multiple constraints, this difference is significant.

**Why greedy hill-climbing over simulated annealing?**  
Simulated annealing requires temperature scheduling. Hill-climbing is simpler, predictable, and the randomness of the initial assignment provides sufficient diversity. For production scale, SA or tabu search would be worth adding.

**Why separate `scoring.py` from `solver.py`?**  
Clean separation of concerns: the solver manages hard constraints and search strategy; the scorer is a pure function from placements → penalty. This makes both independently testable.