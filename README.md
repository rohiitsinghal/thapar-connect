# Thapar Connect

A campus portal for Thapar Institute that generates and publishes the master timetable, and gives students, faculty, and admins role-based access to timetables, courses, exams, rooms, and course material.

## Overview

The system has two main parts:

- **`backend_new/`** — a FastAPI service that:
  - Runs a constraint-based **timetable scheduler** (`scheduler.py`, `genMaster.py`, `extractor.py`) that takes raw Excel inputs (faculty, sections, rooms) and produces a generated master timetable (`output/master_timetable.xlsx`, `output/timetable.json`).
  - Exposes a REST API (`api_server.py`) for the frontend to trigger generation, publish semester settings, and fetch timetables.
  - Handles **auth** for three roles — student, faculty, and admin — via JWT (`auth.py`, `faculty_auth.py`, `admin_auth.py`, `auth_core.py`).
  - Manages **courses** and **course material** (file upload/download) backed by AWS RDS (MySQL) (`courses.py`, `course_material.py`, `rds.py`).
  - Stores student/faculty/course directory data in **AWS DynamoDB** (`db.py`, `import_students.py`, `import_faculty.py`, `import_courses.py`).
  - `backend/` is an older/legacy version of the backend kept alongside `backend_new/`.

- **`Frontend/`** — a React + TypeScript single-page app (Vite, shadcn/ui, Tailwind CSS, TanStack Query) covering:
  - Student/faculty/admin login (`pages/Login.tsx`)
  - Dashboard, Timetable, Exams, Rooms, Courses, Course Material, Course Roster (`pages/`)
  - Admin search and course material management tools

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui (Radix), TanStack Query, React Router, React Hook Form + Zod |
| Backend | Python, FastAPI, Uvicorn |
| Auth | JWT (PyJWT) + bcrypt |
| Databases | AWS DynamoDB (students/faculty/courses directory), AWS RDS MySQL (course material, via `pymysql`) |
| File handling | openpyxl (Excel), python-multipart (uploads) |
| Deployment | AWS |

## Project structure

```
thapar-connect/
├── backend/              # legacy backend (kept for reference)
├── backend_new/          # active FastAPI backend
│   ├── api_server.py     # FastAPI app, routes, CORS, timetable endpoints
│   ├── admin_auth.py     # /auth/admin routes
│   ├── auth.py           # /auth/student routes
│   ├── faculty_auth.py   # /auth/faculty routes
│   ├── auth_core.py      # shared JWT/auth helpers
│   ├── courses.py        # /courses routes
│   ├── course_material.py# /course-material routes (upload/download to RDS)
│   ├── course_catalog.py # course catalog data
│   ├── db.py             # DynamoDB table accessors
│   ├── rds.py            # RDS/MySQL connection helper
│   ├── extractor.py      # parses raw Excel inputs into scheduler data
│   ├── scheduler.py      # constraint-based timetable scheduling engine
│   ├── genMaster.py      # builds the master timetable output
│   ├── master_sync.py    # syncs/imports a master timetable
│   ├── import_students.py, import_faculty.py, import_courses.py
│   │                      # one-off scripts to load data into DynamoDB
│   ├── test.py            # scheduler/pipeline tests
│   ├── data/              # source Excel files (faculty, sections, rooms)
│   ├── output/             # generated timetable.json / master_timetable.xlsx
│   ├── requirements.txt
│   └── .env.example
└── Frontend/
    ├── src/
    │   ├── pages/          # route-level pages (Dashboard, Timetable, Courses, Exams, Rooms, Login, Admin*, ...)
    │   ├── components/     # shared UI components
    │   ├── lib/             # API clients and utilities (coursesApi.ts, etc.)
    │   └── hooks/
    ├── package.json
    └── vite.config.ts
```

## API surface (backend_new)

Mounted routers (see `api_server.py`):

- `/auth/student` — student login/session (`auth.py`)
- `/auth/faculty` — faculty login/session (`faculty_auth.py`)
- `/auth/admin` — admin login/session (`admin_auth.py`)
- `/course-material` — upload/download course material files (`course_material.py`)
- `/courses` — course listings (`courses.py`)

Top-level endpoints (`api_server.py`):

- `GET /health` — health check
- `GET /timetable-data/status` — status of raw uploaded data
- `POST /timetable-data/upload` — upload raw Excel data (faculty/sections/rooms)
- `GET /timetable-settings/publish` / `POST /timetable-settings/publish` — read/set semester publish settings
- `POST /timetable/generate` — run the scheduler and generate a new timetable
- `GET /timetable/latest` — fetch the most recently generated timetable
- `GET /timetable/student/{enrollment_no}` — fetch a student's personal timetable
- `GET /timetable/master` / `POST /timetable/master` — read/import the master timetable

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+ and either `npm` or `bun` (repo has both `package-lock.json` and `bun.lock`)
- AWS credentials configured locally (`aws configure`) for DynamoDB access
- An AWS RDS MySQL instance for course material storage

### Backend setup

```bash
cd backend_new
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in AWS_REGION, RDS_*, AUTH_JWT_SECRET, ADMIN_EMAIL/PASSWORD
uvicorn api_server:app --reload
```

Environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `AWS_REGION` | AWS region for DynamoDB (default `ap-south-1`) |
| `DYNAMODB_STUDENTS_TABLE` | DynamoDB table name for students (default `students`) |
| `AUTH_JWT_SECRET` | Secret used to sign JWTs — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `RDS_HOST` / `RDS_PORT` / `RDS_DB_NAME` / `RDS_USER` / `RDS_PASSWORD` | MySQL RDS connection for course material |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Admin login credentials checked by `/auth/admin/login` |

### Frontend setup

```bash
cd Frontend
npm install     # or: bun install
npm run dev     # starts Vite dev server
```

Other frontend scripts:

```bash
npm run build       # production build
npm run build:dev   # development-mode build
npm run lint         # ESLint
npm run test         # run Vitest tests once
npm run test:watch  # Vitest watch mode
```

### Loading directory data

One-off scripts under `backend_new/` populate DynamoDB/RDS from Excel source files in `backend_new/data/`:

```bash
python import_students.py
python import_faculty.py
python import_courses.py
```

## Deployment

The backend is deployed on AWS (EC2 + RDS + DynamoDB). CORS origins for the deployed frontend are configured in `api_server.py`.

## Notes

- `backend/` is a legacy/earlier implementation retained in the repo; active development is in `backend_new/`.
- Generated timetable artifacts (`output/timetable.json`, `output/master_timetable.xlsx`) are checked into the repo as the current published state.
