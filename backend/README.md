# TIET Timetable Scheduler

Automated university timetable generator for Thapar Institute of Engineering & Technology (TIET), Patiala. Schedules all 8 semesters across 8 departments using a Simulated Annealing solver — the same core algorithm as UniTime.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Data Model](#data-model)
- [Solver Pipeline](#solver-pipeline)
- [Solver vs UniTime](#solver-vs-unitime)
- [Sample Data (TIET Scale)](#sample-data-tiet-scale)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [File Structure](#file-structure)
- [How to Extend](#how-to-extend)

---

## Quick Start

```bash
# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic-settings

# 2. Configure your database and settings
cp .env.example .env
# Edit DATABASE_URL and any other values in .env

# 3. Seed the database (wipes existing data, reseeds from scratch)
cd backend
python -m app.seed.seed_data

# 4. Start the server
uvicorn app.main:app --reload

# 5. Schedule a single semester
curl -X POST http://localhost:8000/generate-timetable/1

# 6. Or schedule all 8 semesters at once
curl -X POST http://localhost:8000/generate-timetable/all

# 7. View the timetable for a department
curl http://localhost:8000/timetable/1/department/COE
```

---

## Architecture Overview

The system is organised into four layers. Config flows down into every layer. The API layer triggers the service layer, which reads from and writes to PostgreSQL via the ORM.

```
┌─────────────────────────────────────────────────────────────┐
│  CONFIG LAYER                                               │
│  .env  ──►  config.py (Settings class — all tunables)      │
├─────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                 │
│  models.py      ORM entities (Teacher, Room, Batch,        │
│                 Subject, TimetableEntry)                    │
│  seed_data.py   Populates DB: 8 depts × 4 yrs × 2 sems    │
│  schemas.py     Pydantic DTOs for API responses            │
│  timeslots.py   55 valid Mon–Fri 08:00–17:10 slots         │
├─────────────────────────────────────────────────────────────┤
│  SERVICE LAYER                                              │
│  scoring.py     compute_penalty() — 5 soft constraints     │
│  solver.py      run_solver(db, semester) — SA algorithm    │
│  optimizer.py   persist_timetable() — DB write + console   │
├─────────────────────────────────────────────────────────────┤
│  API LAYER                                                  │
│  api/timetable.py   FastAPI router — all endpoints         │
│  main.py            App entrypoint, includes router        │
├─────────────────────────────────────────────────────────────┤
│  STORAGE                                                    │
│  PostgreSQL — teachers · rooms · batches · subjects        │
│               timetable_entries                            │
└─────────────────────────────────────────────────────────────┘
```

### File → destination mapping

| File delivered | Place in project |
|---|---|
| `.env` | `backend/.env` |
| `config.py` | `backend/app/core/config.py` |
| `models.py` | `backend/app/models/models.py` |
| `seed_data.py` | `backend/app/seed/seed_data.py` |
| `solver.py` | `backend/app/services/solver.py` |
| `scoring.py` | `backend/app/services/scoring.py` |
| `optimizer.py` | `backend/app/services/optimizer.py` |
| `router.py` | `backend/app/api/timetable.py` |
| `schemas.py` | `backend/app/schemas/schemas.py` |

### Registering the router in `main.py`

```python
from app.api.timetable import router
app.include_router(router)
```

---

## Data Model

Five ORM entities. Fields marked `NEW` were added in the full-scale version.

```
Teacher                    Subject
───────                    ───────
id          PK             id                PK
name                       name
department  NEW            semester          NEW  (1–8)
                           subject_type      NEW  (core/elective)
                           lectures_per_week
                           teacher_id        FK → Teacher
                           batch_id          FK → Batch

Room                       Batch
────                       ─────
id          PK             id                PK
name                       name              (e.g. COE-Y1-A)
capacity                   department        NEW  (e.g. COE)
                           size              (students)
                           year              (1–4)

TimetableEntry
──────────────
id
semester    NEW  (1–8)   ← allows entries from different semesters
day              (0–4, Mon–Fri)    to coexist without room conflicts
slot_index       (0–10)
teacher_id  FK → Teacher
room_id     FK → Room
batch_id    FK → Batch
subject_id  FK → Subject

Unique constraints (database-level hard constraint enforcement):
  (teacher_id, day, slot_index, semester)
  (room_id,    day, slot_index, semester)
  (batch_id,   day, slot_index, semester)
```

### Why `semester` is on `Subject`, not `Batch`

Each batch exists once (e.g. `COE-Y1-A`). A batch has subjects in Semester 1 AND Semester 2 — those are different rows in the `subjects` table, tagged with `semester=1` or `semester=2`. The solver filters `WHERE semester = N` each run, so each scheduling run is completely isolated.

---

## Solver Pipeline

A single call to `POST /generate-timetable/1` executes this sequence:

```
POST /generate-timetable/1
        │
        ▼
router.py — validate semester in range [1, 8]
        │
        ▼
solver.run_solver(db, semester=1)
  │
  ├── Load: Subject WHERE semester=1  (~200–300 subjects at full scale)
  │         Room (all 30)
  │         Batch (all 100+)
  │
  ├── PHASE 3 — Random greedy initial assignment
  │     For each task (subject × lectures_per_week), shuffled:
  │       Try random timeslots × rooms until one passes all hard constraints:
  │         HC-1  teacher not double-booked
  │         HC-2  room not double-booked
  │         HC-3  batch not double-booked
  │         HC-4  room.capacity >= batch.size
  │         HC-5  same subject not placed twice on same day
  │       Retry up to SOLVER_MAX_RETRIES times if a task can't be placed
  │
  ├── PHASE 4 — Score initial assignment
  │     compute_penalty() returns integer ≥ 0 (lower = better)
  │
  └── PHASE 5 — Simulated Annealing (SOLVER_ITERATIONS moves)
        Temperature: SA_T_START → SA_T_END  (geometric decay)
        Each iteration picks a random placement and tries 3 move types:
          Move 1: relocate to a new timeslot (same room)
          Move 2: relocate to a new room     (same timeslot)
          Move 3: swap timeslots with another random placement
        Acceptance: always accept if score improves;
                    accept with P = exp(-Δ/T) if score worsens
        Best state across all iterations is kept

optimizer.persist_timetable(placements, semester=1)
  │
  ├── DELETE timetable_entries WHERE semester=1  (other sems untouched)
  ├── INSERT all new entries (bulk)
  └── Print console output (if PRINT_TIMETABLE_CONSOLE=true)
          grouped: department → semester → batch → day → slot
```

---

## Soft Constraints (Penalty Functions)

`scoring.py` runs five penalty functions. The solver minimises the total:

| Penalty | Points | Description |
|---|---|---|
| Same subject, same day | +50 per extra | A batch should never have two sessions of the same subject on the same day |
| Consecutive overload | +10 × (run−4) | Teacher or batch with more than 4 consecutive slots |
| Teacher workload imbalance | +5 × deviation | Teacher's daily load deviates more than 1 from their weekly average |
| Batch schedule gaps | +3 per gap | Two or more free slots sandwiched between lectures in a batch's day |
| Lecture clustering | +2 × deviation | Batch lectures bunched on fewer days than average |

A score of 0 means every soft constraint is perfectly satisfied. The solver exits early if this is reached.

---

## Solver vs UniTime

The algorithm mirrors UniTime's documented approach. Five elements are identical; three are intentionally simplified.

| Element | This solver | UniTime |
|---|---|---|
| Hard constraints | Teacher / Room / Batch conflict sets | Same |
| Soft constraints | Weighted penalty score | Same (weighted criteria) |
| Initial solution | Random greedy | Same |
| Optimisation algorithm | Simulated Annealing | Same |
| Move types | Relocate + Swap | Same |
| Conflict detection | 3 Python hash sets, O(1) | Full constraint propagation graph |
| Restarts | Single SA run | Multi-start SA with temperature reheating |
| Problem decomposition | All batches in one run | Room / time assignment separated |

For scheduling one institution's timetable, the simplified approach produces results equivalent in structure to UniTime's output. The main practical difference is that UniTime's multi-start restarts give marginally better soft-constraint satisfaction on very large datasets.

---

## Sample Data (TIET Scale)

Seeded from the official TIET 2025-26 admission document (3 390 total BTech seats across 19 programmes). The seed covers 8 programmes with data-driven batch sizes.

### Department breakdown

| Dept | Full name | Annual intake | Per year | Sections | Batch size |
|---|---|---|---|---|---|
| COE | Computer Engineering | 960 | 240 | A + B | 120 each |
| ECE | Electronics & Communication | 240 | 60 | 1 | 60 |
| MEE | Mechanical Engineering | 120 | 30 | 1 | 30 |
| CHE | Chemical Engineering | 60 | 15 | 1 | 15 |
| CIE | Civil Engineering | 90 | 22 | 1 | 22 |
| ELE | Electrical Engineering | 90 | 22 | 1 | 22 |
| AIML | AI & Machine Learning | 240 | 60 | 1 | 60 |
| ENC | Electronics & Computer | 360 | 90 | A + B | 45 each |

### Scale at full seeding

| Entity | Count |
|---|---|
| Departments | 8 |
| Teachers | ~120 |
| Rooms | 30 |
| Batches | ~100 (sections included) |
| Subjects | ~2 000 (8 sems × all batches × 5 subjects) |
| Lectures to schedule per semester | ~500–600 |
| Available weekly slots (55 × 30 rooms) | 1 650 |

### Room inventory

| Block | Type | Capacity | Count |
|---|---|---|---|
| A-LH | Large lecture hall | 300 | 5 |
| B-LH | Medium lecture hall | 180 | 4 |
| C-SR | Seminar room | 120 | 4 |
| D-TR | Tutorial room | 60 | 5 |
| E-CL | Computer lab | 40 | 4 |
| F-EL | Electronics lab | 30 | 3 |
| G-ML | Mech / Chem / Civil lab | 25 | 5 |

### Semester numbering (TIET convention)

```
Year 1  →  Semester 1 (odd)   Semester 2 (even)
Year 2  →  Semester 3         Semester 4
Year 3  →  Semester 5         Semester 6
Year 4  →  Semester 7         Semester 8
```

---

## Configuration Reference

Every variable below lives in `.env`. Change any of them without touching Python code.

### Academic structure

| Variable | Default | Description |
|---|---|---|
| `ACADEMIC_YEARS` | `4` | Number of years in the programme |
| `SEMESTERS_PER_YEAR` | `2` | Semesters per year (2 → 8 total) |
| `SUBJECTS_PER_BATCH_PER_SEMESTER` | `5` | How many subjects each batch gets per semester |
| `LECTURES_PER_WEEK_CORE` | `3` | Weekly lectures for core/theory subjects |
| `LECTURES_PER_WEEK_ELECTIVE` | `2` | Weekly lectures for elective/lab subjects |

### Departments and intake

| Variable | Default | Description |
|---|---|---|
| `ACTIVE_DEPARTMENTS` | `COE,ECE,MEE,...` | Comma-separated list — remove a code to exclude it |
| `SECTION_SPLIT_THRESHOLD` | `180` | Per-year batch size above which a dept splits into A+B sections |
| `INTAKE_COE` | `960` | Annual total intake for COE |
| `INTAKE_ECE` | `240` | Annual total intake for ECE |
| `INTAKE_MEE` | `120` | … and so on for each dept |

### Room inventory

| Variable | Default | Description |
|---|---|---|
| `ROOMS_300` | `5` | Number of 300-seat lecture halls |
| `ROOMS_180` | `4` | Number of 180-seat halls |
| `ROOMS_120` | `4` | Number of 120-seat seminar rooms |
| `ROOMS_60` | `5` | Number of 60-seat tutorial rooms |
| `ROOMS_40` | `4` | Number of 40-seat computer labs |
| `ROOMS_30` | `3` | Number of 30-seat electronics labs |
| `ROOMS_25` | `5` | Number of 25-seat specialist labs |

### Solver (Simulated Annealing)

| Variable | Default | Description |
|---|---|---|
| `SOLVER_MAX_RETRIES` | `15` | Attempts to build a valid initial assignment |
| `SOLVER_ITERATIONS` | `20000` | Total SA moves per semester run |
| `SA_T_START` | `300.0` | Initial temperature — set ≈ expected initial penalty |
| `SA_T_END` | `0.1` | Final temperature — below this SA = hill-climbing |

**Tuning tip:** If the solver reports a high final penalty score, increase `SA_T_START` and `SOLVER_ITERATIONS`. If it's slow, decrease `SOLVER_ITERATIONS` first and check whether quality drops.

### Output

| Variable | Default | Description |
|---|---|---|
| `PRINT_TIMETABLE_CONSOLE` | `true` | Print full timetable to terminal after generation |
| `LOG_LEVEL` | `INFO` | Python log level: DEBUG, INFO, WARNING, ERROR |

---

## API Reference

### Generation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate-timetable/{semester}` | Run solver for one semester (1–8), persist result |
| `POST` | `/generate-timetable/all` | Run solver for all 8 semesters sequentially |

**Response for single semester:**
```json
{
  "semester": 1,
  "penalty_score": 12,
  "lectures_count": 487,
  "message": "Semester 1 scheduled: 487 lectures, penalty=12."
}
```

### Retrieval

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/timetable/{semester}` | All entries for a semester |
| `GET` | `/timetable/{semester}/batch/{batch_id}` | One batch's week |
| `GET` | `/timetable/{semester}/room/{room_id}` | One room's week |
| `GET` | `/timetable/{semester}/teacher/{teacher_id}` | One teacher's week |
| `GET` | `/timetable/{semester}/department/{dept_code}` | All batches for a dept |

**Example entry in response:**
```json
{
  "id": 142,
  "semester": 1,
  "day": 0,
  "slot_index": 2,
  "day_name": "Monday",
  "start_time": "09:40",
  "end_time": "10:30",
  "teacher_id": 3,
  "teacher_name": "Prof. Amandeep Singh",
  "room_id": 7,
  "room_name": "A-LH3",
  "batch_id": 1,
  "batch_name": "COE-Y1-A",
  "department": "COE",
  "subject_id": 11,
  "subject_name": "Programming Fundamentals"
}
```

---

## Console Output Format

When `PRINT_TIMETABLE_CONSOLE=true`, after each solver run you will see:

```
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
  GENERATED TIMETABLE — SEMESTER 1
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

#######################################################################
  DEPARTMENT: COE   SEMESTER: 1
#######################################################################

  =====================================================================
  BATCH: COE-Y1-A  (15 lectures this week)
  =====================================================================

    Monday
    ---------------------------------------------------------------------
    08:00 - 08:50  │  Programming Fundamentals
                   │  Prof. Amandeep Singh          │  A-LH3
    09:40 - 10:30  │  Discrete Structures
                   │  Dr. Priya Nair                │  A-LH1
    ---------------------------------------------------------------------

    Tuesday
    ...
```

---

## File Structure

```
backend/
├── .env                          ← all tunables (never commit to git)
├── app/
│   ├── main.py                   ← FastAPI app, includes router
│   ├── core/
│   │   ├── config.py             ← Settings class (reads .env)
│   │   └── database.py           ← SQLAlchemy engine + SessionLocal
│   ├── models/
│   │   └── models.py             ← ORM: Teacher, Room, Batch, Subject,
│   │                                       TimetableEntry
│   ├── schemas/
│   │   └── schemas.py            ← Pydantic DTOs
│   ├── api/
│   │   └── timetable.py          ← FastAPI router (was router.py)
│   ├── services/
│   │   ├── scoring.py            ← soft-constraint penalty functions
│   │   ├── solver.py             ← Simulated Annealing solver
│   │   └── optimizer.py         ← DB persistence + console output
│   ├── seed/
│   │   └── seed_data.py          ← TIET full-scale seed
│   └── utils/
│       └── timeslots.py          ← 55 valid weekly slots
└── requirements.txt
```

---

## How to Extend

### Change the number of subjects per semester

Edit `.env`:
```
SUBJECTS_PER_BATCH_PER_SEMESTER=6
```
The curriculum lists in `seed_data.py` already have 8 subjects per semester defined — the seed just slices the first N. Re-run `python -m app.seed.seed_data` to apply.

### Add a new department

1. Add the department code to `ACTIVE_DEPARTMENTS` in `.env`
2. Add `INTAKE_<CODE>=<number>` in `.env`
3. Add the same key to `Settings.intake_map` in `config.py`
4. Add a teacher pool to `TEACHER_POOL` in `seed_data.py`
5. Add an 8-semester curriculum to `CURRICULUM` in `seed_data.py`
6. Re-run the seed

### Add more rooms

Edit `.env`:
```
ROOMS_300=8
ROOMS_180=6
```
Re-run the seed.

### Improve solution quality

Increase iteration count and starting temperature in `.env`:
```
SOLVER_ITERATIONS=50000
SA_T_START=500.0
```
No code changes needed.

### Schedule a specific department only

Use the API:
```bash
# After generating semester 1:
curl http://localhost:8000/timetable/1/department/COE
```

---

## Timeslot Grid

Mon–Fri, 08:00–17:10, 50-minute slots with a 10-minute break built in between each:

| Slot | Start | End |
|---|---|---|
| 0 | 08:00 | 08:50 |
| 1 | 08:50 | 09:40 |
| 2 | 09:40 | 10:30 |
| 3 | 10:30 | 11:20 |
| 4 | 11:20 | 12:10 |
| 5 | 12:10 | 13:00 |
| 6 | 13:00 | 13:50 |
| 7 | 13:50 | 14:40 |
| 8 | 14:40 | 15:30 |
| 9 | 15:30 | 16:20 |
| 10 | 16:20 | 17:10 |

5 days × 11 slots = **55 slots per week** per room.

---

## Hard Constraints (never violated)

These are enforced both in the solver via O(1) hash-set lookups and at the database level via `UNIQUE` constraints:

1. A teacher cannot be in two places at the same time in the same semester
2. A room cannot host two classes simultaneously in the same semester
3. A batch cannot attend two classes simultaneously in the same semester
4. A room's capacity must be ≥ the batch size
5. Each subject must be scheduled exactly `lectures_per_week` times per week
6. All scheduled slots must be valid (Mon–Fri, slots 0–10 only)
7. The same subject cannot appear twice on the same day for the same batch

---

*Built on FastAPI · SQLAlchemy · PostgreSQL · Pydantic · Simulated Annealing*