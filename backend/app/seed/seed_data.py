"""
Seed script — populates the database with realistic test data.

Creates:
  - 10 teachers
  - 10 rooms  (varied capacity to make room-capacity constraint interesting)
  - 4 batches (different years and sizes)
  - 20 subjects (mix of 2 and 3 lectures per week)

Run with:
    python -m app.seed.seed_data

or directly:
    python app/seed/seed_data.py
"""

import sys
import os

# Allow running the script directly from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.database import SessionLocal, engine, Base
from app.models.models import Teacher, Room, Batch, Subject


def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ── Guard: don't double-seed ─────────────────────────────────────────
        if db.query(Teacher).count() > 0:
            print("Database already seeded — skipping.")
            return

        # ── Teachers ─────────────────────────────────────────────────────────
        teachers = [
            Teacher(name="Dr. Alice Mercer"),
            Teacher(name="Prof. Bob Kwan"),
            Teacher(name="Dr. Carol Singh"),
            Teacher(name="Prof. David Osei"),
            Teacher(name="Dr. Eva Richter"),
            Teacher(name="Prof. Frank Delacroix"),
            Teacher(name="Dr. Grace Tanaka"),
            Teacher(name="Prof. Henry Johansson"),
            Teacher(name="Dr. Isla Patel"),
            Teacher(name="Prof. James Okoro"),
        ]
        db.add_all(teachers)
        db.flush()      # get IDs without committing
        print(f"Added {len(teachers)} teachers.")

        # ── Rooms ─────────────────────────────────────────────────────────────
        # Capacity varies: some rooms are small labs, others large lecture halls
        rooms = [
            Room(name="LH-101",  capacity=200),  # large lecture hall
            Room(name="LH-102",  capacity=150),
            Room(name="LH-103",  capacity=120),
            Room(name="SR-201",  capacity=60),   # seminar rooms
            Room(name="SR-202",  capacity=60),
            Room(name="SR-203",  capacity=40),
            Room(name="LAB-301", capacity=30),   # computer labs
            Room(name="LAB-302", capacity=30),
            Room(name="LAB-303", capacity=25),
            Room(name="TUT-401", capacity=20),   # tutorial rooms
        ]
        db.add_all(rooms)
        db.flush()
        print(f"Added {len(rooms)} rooms.")

        # ── Batches ───────────────────────────────────────────────────────────
        # Year 1–4, sizes chosen to test capacity constraints
        batches = [
            Batch(name="CS-Year1-A", size=110, year=1),
            Batch(name="CS-Year2-B", size=55,  year=2),
            Batch(name="CS-Year3-C", size=28,  year=3),
            Batch(name="CS-Year4-D", size=18,  year=4),
        ]
        db.add_all(batches)
        db.flush()
        print(f"Added {len(batches)} batches.")

        # ── Subjects ──────────────────────────────────────────────────────────
        # 5 subjects per batch.  Teacher assignments are spread across batches.
        # lectures_per_week alternates between 2 and 3.
        t  = teachers   # shorthand
        b  = batches    # shorthand

        subjects = [
            # Year 1
            Subject(name="Introduction to Programming",  teacher_id=t[0].id, batch_id=b[0].id, lectures_per_week=3),
            Subject(name="Discrete Mathematics",         teacher_id=t[1].id, batch_id=b[0].id, lectures_per_week=3),
            Subject(name="Linear Algebra",               teacher_id=t[2].id, batch_id=b[0].id, lectures_per_week=2),
            Subject(name="Digital Logic Design",         teacher_id=t[3].id, batch_id=b[0].id, lectures_per_week=2),
            Subject(name="English Communication",        teacher_id=t[4].id, batch_id=b[0].id, lectures_per_week=2),

            # Year 2
            Subject(name="Data Structures & Algorithms", teacher_id=t[0].id, batch_id=b[1].id, lectures_per_week=3),
            Subject(name="Database Systems",             teacher_id=t[5].id, batch_id=b[1].id, lectures_per_week=2),
            Subject(name="Computer Networks",            teacher_id=t[6].id, batch_id=b[1].id, lectures_per_week=2),
            Subject(name="Operating Systems",            teacher_id=t[7].id, batch_id=b[1].id, lectures_per_week=3),
            Subject(name="Object-Oriented Programming",  teacher_id=t[1].id, batch_id=b[1].id, lectures_per_week=2),

            # Year 3
            Subject(name="Software Engineering",         teacher_id=t[5].id, batch_id=b[2].id, lectures_per_week=2),
            Subject(name="Artificial Intelligence",      teacher_id=t[8].id, batch_id=b[2].id, lectures_per_week=2),
            Subject(name="Web Technologies",             teacher_id=t[9].id, batch_id=b[2].id, lectures_per_week=2),
            Subject(name="Theory of Computation",        teacher_id=t[2].id, batch_id=b[2].id, lectures_per_week=3),
            Subject(name="Computer Graphics",            teacher_id=t[3].id, batch_id=b[2].id, lectures_per_week=2),

            # Year 4
            Subject(name="Machine Learning",             teacher_id=t[8].id, batch_id=b[3].id, lectures_per_week=3),
            Subject(name="Distributed Systems",          teacher_id=t[7].id, batch_id=b[3].id, lectures_per_week=2),
            Subject(name="Cloud Computing",              teacher_id=t[6].id, batch_id=b[3].id, lectures_per_week=2),
            Subject(name="Cybersecurity",                teacher_id=t[9].id, batch_id=b[3].id, lectures_per_week=2),
            Subject(name="Research Methodology",         teacher_id=t[4].id, batch_id=b[3].id, lectures_per_week=2),
        ]
        db.add_all(subjects)
        db.commit()
        print(f"Added {len(subjects)} subjects.")

        # ── Summary ───────────────────────────────────────────────────────────
        total_lectures = sum(s.lectures_per_week for s in subjects)
        print(f"\nSeed complete!  Total lecture slots to schedule: {total_lectures}")
        print("Run POST /generate-timetable to build the timetable.")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()