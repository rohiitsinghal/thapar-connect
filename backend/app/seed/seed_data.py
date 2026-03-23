"""
Seed script — TIET Patiala, full 8-semester schedule.

Reads all counts from settings (which reads from .env), so you can change
SUBJECTS_PER_BATCH_PER_SEMESTER, INTAKE_*, ACTIVE_DEPARTMENTS etc. in .env
without touching this file.

Academic structure
──────────────────
  8 departments  : COE, ECE, MEE, CHE, CIE, ELE, AIML, ENC
  4 years        : Y1–Y4
  2 semesters/yr : odd semester (1,3,5,7) and even semester (2,4,6,8)
  5 subjects/sem : 3 core (3 lec/wk) + 2 elective (2 lec/wk) per batch

Semester numbering (TIET convention)
  Year 1 → Semesters 1, 2
  Year 2 → Semesters 3, 4
  Year 3 → Semesters 5, 6
  Year 4 → Semesters 7, 8

Sections
  Branches with annual intake > SECTION_SPLIT_THRESHOLD get two sections
  (A and B) each of size ≈ intake/year/2.
  Currently: COE (960) and ENC (360) split; all others are single-section.

Run:
    python -m app.seed.seed_data
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.database import SessionLocal, engine, Base
from app.core.config   import settings
from app.models.models import Teacher, Room, Batch, Subject, TimetableEntry


# ── Curriculum definitions ────────────────────────────────────────────────────
# Each entry: (subject_name, subject_type)
# subject_type "core" → LECTURES_PER_WEEK_CORE lec/wk
#              "elective" → LECTURES_PER_WEEK_ELECTIVE lec/wk
#
# 5 subjects per semester per batch:  3 core + 2 elective
# Semesters follow TIET odd/even per year.

CURRICULUM = {
    # ── COE / AIML / ENC share a common CS base in Y1─Y2 ────────────────────
    "COE": {
        1: [("Programming Fundamentals",       "core"),
            ("Discrete Structures",            "core"),
            ("Engineering Mathematics I",      "core"),
            ("Digital Electronics",            "elective"),
            ("Communication Skills",           "elective")],
        2: [("Data Structures",                "core"),
            ("Computer Organisation",          "core"),
            ("Engineering Mathematics II",     "core"),
            ("Object-Oriented Programming",    "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Algorithms",                     "core"),
            ("Operating Systems",              "core"),
            ("Probability & Statistics",       "core"),
            ("Database Management Systems",    "elective"),
            ("Computer Networks",              "elective")],
        4: [("Theory of Computation",          "core"),
            ("Software Engineering",           "core"),
            ("Microprocessors",                "core"),
            ("Web Technologies",               "elective"),
            ("Numerical Methods",              "elective")],
        5: [("Compiler Design",                "core"),
            ("Artificial Intelligence",        "core"),
            ("Information Security",           "core"),
            ("Cloud Computing",                "elective"),
            ("Mobile App Development",         "elective")],
        6: [("Machine Learning",               "core"),
            ("Distributed Systems",            "core"),
            ("Big Data Analytics",             "core"),
            ("IoT Systems",                    "elective"),
            ("DevOps Practices",               "elective")],
        7: [("Deep Learning",                  "core"),
            ("Natural Language Processing",    "core"),
            ("Blockchain Technology",          "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Advanced Algorithms",            "core"),
            ("Edge Computing",                 "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "ECE": {
        1: [("Basic Electronics",              "core"),
            ("Circuit Theory",                 "core"),
            ("Engineering Mathematics I",      "core"),
            ("Engineering Drawing",            "elective"),
            ("Communication Skills",           "elective")],
        2: [("Signals & Systems",              "core"),
            ("Analog Electronics",             "core"),
            ("Engineering Mathematics II",     "core"),
            ("Programming for Engineers",      "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Digital Communication",          "core"),
            ("Electromagnetic Theory",         "core"),
            ("Control Systems",                "core"),
            ("Microcontrollers",               "elective"),
            ("VLSI Design",                    "elective")],
        4: [("Antenna & Wave Propagation",     "core"),
            ("Analog Communication",           "core"),
            ("Signal Processing",              "core"),
            ("PCB Design",                     "elective"),
            ("Embedded Systems",               "elective")],
        5: [("Wireless Communication",         "core"),
            ("Optical Fiber Communication",    "core"),
            ("Digital Signal Processing",      "core"),
            ("IoT and Sensors",                "elective"),
            ("RF Circuit Design",              "elective")],
        6: [("5G Networks",                    "core"),
            ("Image Processing",               "core"),
            ("Satellite Communication",        "core"),
            ("Radar Systems",                  "elective"),
            ("Speech Processing",              "elective")],
        7: [("Advanced VLSI",                  "core"),
            ("Machine Learning for ECE",       "core"),
            ("Mixed Signal Design",            "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Spectrum Management",            "core"),
            ("Nano Electronics",               "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "MEE": {
        1: [("Engineering Mechanics",          "core"),
            ("Engineering Mathematics I",      "core"),
            ("Engineering Drawing",            "core"),
            ("Workshop Technology",            "elective"),
            ("Communication Skills",           "elective")],
        2: [("Strength of Materials",          "core"),
            ("Engineering Mathematics II",     "core"),
            ("Thermodynamics",                 "core"),
            ("Manufacturing Processes",        "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Fluid Mechanics",                "core"),
            ("Theory of Machines",             "core"),
            ("Material Science",               "core"),
            ("Metrology & Quality",            "elective"),
            ("CAD/CAM",                        "elective")],
        4: [("Heat Transfer",                  "core"),
            ("Machine Design",                 "core"),
            ("Industrial Engineering",         "core"),
            ("Refrigeration & AC",             "elective"),
            ("Vibration Analysis",             "elective")],
        5: [("Dynamics of Machinery",          "core"),
            ("Finite Element Analysis",        "core"),
            ("Operations Research",            "core"),
            ("Power Plant Engineering",        "elective"),
            ("Tribology",                      "elective")],
        6: [("Robotics & Automation",          "core"),
            ("Mechatronics",                   "core"),
            ("Production Planning",            "core"),
            ("Non-Destructive Testing",        "elective"),
            ("Additive Manufacturing",         "elective")],
        7: [("Advanced Manufacturing",         "core"),
            ("Industry 4.0",                   "core"),
            ("Vehicle Dynamics",               "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Smart Manufacturing",            "core"),
            ("Renewable Energy Systems",       "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "CHE": {
        1: [("Chemical Engg Fundamentals",     "core"),
            ("Engineering Chemistry",          "core"),
            ("Engineering Mathematics I",      "core"),
            ("Material & Energy Balances",     "elective"),
            ("Communication Skills",           "elective")],
        2: [("Fluid Flow Operations",          "core"),
            ("Engineering Mathematics II",     "core"),
            ("Thermodynamics (Chem)",          "core"),
            ("Chemical Process Calculations",  "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Heat Transfer Operations",       "core"),
            ("Chemical Reaction Engineering",  "core"),
            ("Mass Transfer I",                "core"),
            ("Process Instrumentation",        "elective"),
            ("Transport Phenomena",            "elective")],
        4: [("Mass Transfer II",               "core"),
            ("Process Control",                "core"),
            ("Separation Processes",           "core"),
            ("Petroleum Refining",             "elective"),
            ("Polymer Engineering",            "elective")],
        5: [("Chemical Plant Design I",        "core"),
            ("Catalysis & Reaction Kinetics",  "core"),
            ("Environmental Engineering",      "core"),
            ("Energy Technology",              "elective"),
            ("Biochemical Engineering",        "elective")],
        6: [("Chemical Plant Design II",       "core"),
            ("Safety & Hazard Analysis",       "core"),
            ("Process Optimisation",           "core"),
            ("Green Chemistry",                "elective"),
            ("Nanomaterials",                  "elective")],
        7: [("Advanced Separation",            "core"),
            ("Computational Fluid Dynamics",   "core"),
            ("Industrial Waste Treatment",     "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Advanced Process Control",       "core"),
            ("Carbon Capture Technology",      "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "CIE": {
        1: [("Engineering Mechanics (Civil)",  "core"),
            ("Engineering Mathematics I",      "core"),
            ("Engineering Drawing (Civil)",    "core"),
            ("Building Materials",             "elective"),
            ("Communication Skills",           "elective")],
        2: [("Structural Analysis I",          "core"),
            ("Engineering Mathematics II",     "core"),
            ("Surveying",                      "core"),
            ("Geotechnical Engineering I",     "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Structural Analysis II",         "core"),
            ("Fluid Mechanics (Civil)",        "core"),
            ("Concrete Technology",            "core"),
            ("Geotechnical Engineering II",    "elective"),
            ("Quantity Surveying",             "elective")],
        4: [("Steel Structure Design",         "core"),
            ("Transportation Engineering",     "core"),
            ("Water Resources Engineering",    "core"),
            ("Foundation Engineering",         "elective"),
            ("Construction Management",        "elective")],
        5: [("Advanced Structural Design",     "core"),
            ("Environmental Engineering",      "core"),
            ("Remote Sensing & GIS",           "core"),
            ("Urban Planning",                 "elective"),
            ("Bridge Engineering",             "elective")],
        6: [("Earthquake Engineering",         "core"),
            ("Pavement Design",                "core"),
            ("Wastewater Treatment",           "core"),
            ("Smart Cities",                   "elective"),
            ("Solid Waste Management",         "elective")],
        7: [("Advanced Foundation Design",     "core"),
            ("Infrastructure Management",      "core"),
            ("Sustainable Construction",       "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Green Building Design",          "core"),
            ("Disaster Management",            "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "ELE": {
        1: [("Basic Electrical Engineering",   "core"),
            ("Engineering Mathematics I",      "core"),
            ("Circuit Analysis",               "core"),
            ("Workshop / Electrical",          "elective"),
            ("Communication Skills",           "elective")],
        2: [("Electromagnetic Fields",         "core"),
            ("Engineering Mathematics II",     "core"),
            ("Analog Electronics (ELE)",       "core"),
            ("Electrical Measurements",        "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Electrical Machines I",          "core"),
            ("Signals & Systems (ELE)",        "core"),
            ("Digital Electronics (ELE)",      "core"),
            ("Control Systems (ELE)",          "elective"),
            ("Power Systems I",                "elective")],
        4: [("Electrical Machines II",         "core"),
            ("Power Electronics",              "core"),
            ("Microprocessors (ELE)",          "core"),
            ("Power Systems II",               "elective"),
            ("Switchgear & Protection",        "elective")],
        5: [("High Voltage Engineering",       "core"),
            ("Digital Signal Processing (ELE)","core"),
            ("Power System Analysis",          "core"),
            ("Drives & Controls",              "elective"),
            ("FACTS Technology",               "elective")],
        6: [("Smart Grid Technology",          "core"),
            ("Electric Vehicles",              "core"),
            ("Renewable Energy Systems",       "core"),
            ("Power Quality",                  "elective"),
            ("Energy Auditing",                "elective")],
        7: [("Advanced Power Systems",         "core"),
            ("Machine Learning for ELE",       "core"),
            ("Micro Grid Systems",             "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Power System Protection",        "core"),
            ("Battery Technology",             "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "AIML": {
        1: [("Programming Fundamentals",       "core"),
            ("Engineering Mathematics I",      "core"),
            ("Introduction to AI",             "core"),
            ("Digital Logic",                  "elective"),
            ("Communication Skills",           "elective")],
        2: [("Data Structures",                "core"),
            ("Engineering Mathematics II",     "core"),
            ("Probability & Statistics",       "core"),
            ("Python for Data Science",        "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Machine Learning I",             "core"),
            ("Linear Algebra for AI",          "core"),
            ("Database Systems",               "core"),
            ("Computer Vision Basics",         "elective"),
            ("NLP Basics",                     "elective")],
        4: [("Machine Learning II",            "core"),
            ("Deep Learning I",                "core"),
            ("Big Data Systems",               "core"),
            ("Reinforcement Learning",         "elective"),
            ("Cloud for ML",                   "elective")],
        5: [("Deep Learning II",               "core"),
            ("Computer Vision",                "core"),
            ("Natural Language Processing",    "core"),
            ("MLOps",                          "elective"),
            ("Generative AI",                  "elective")],
        6: [("Advanced NLP",                   "core"),
            ("AI Ethics & Fairness",           "core"),
            ("Autonomous Systems",             "core"),
            ("Federated Learning",             "elective"),
            ("Graph Neural Networks",          "elective")],
        7: [("Foundation Models",              "core"),
            ("AI for Healthcare",              "core"),
            ("Explainable AI",                 "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("AI Systems Design",              "core"),
            ("Edge AI",                        "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },

    "ENC": {
        1: [("Basic Electronics",              "core"),
            ("Programming Fundamentals",       "core"),
            ("Engineering Mathematics I",      "core"),
            ("Digital Electronics",            "elective"),
            ("Communication Skills",           "elective")],
        2: [("Circuit Theory",                 "core"),
            ("Data Structures",                "core"),
            ("Engineering Mathematics II",     "core"),
            ("Signals & Systems",              "elective"),
            ("Environmental Studies",          "elective")],
        3: [("Computer Organisation",          "core"),
            ("Analog Electronics",             "core"),
            ("Operating Systems",              "core"),
            ("Embedded C Programming",         "elective"),
            ("VLSI Fundamentals",              "elective")],
        4: [("Computer Networks",              "core"),
            ("Digital Communication",          "core"),
            ("Database Systems",               "core"),
            ("Wireless Sensor Networks",       "elective"),
            ("Microcontrollers",               "elective")],
        5: [("Software Engineering",           "core"),
            ("RF & Microwave Engineering",     "core"),
            ("Machine Learning",               "core"),
            ("IoT Architecture",               "elective"),
            ("Cloud Computing",                "elective")],
        6: [("5G and Beyond",                  "core"),
            ("Deep Learning",                  "core"),
            ("Cyber Security",                 "core"),
            ("Edge AI",                        "elective"),
            ("Full Stack Development",         "elective")],
        7: [("Advanced Computer Networks",     "core"),
            ("AI for Signal Processing",       "core"),
            ("Autonomous Systems",             "core"),
            ("Research Methodology",           "elective"),
            ("Entrepreneurship",               "elective")],
        8: [("Capstone Project I",             "core"),
            ("Next-Gen Communication",         "core"),
            ("Quantum Computing Basics",       "core"),
            ("Technical Communication",        "elective"),
            ("Professional Ethics",            "elective")],
    },
}

# ── Teacher pool per department ───────────────────────────────────────────────
# We need enough teachers so no one is double-booked across batches/semesters.
# Rule: 1 teacher per subject per unique (batch, semester) combination.
# For multi-section depts (COE, ENC) each section needs its own teacher per subject.
# We assign teachers round-robin within the dept pool.

TEACHER_POOL = {
    "COE":  [
        "Prof. Rajesh Kumar Sharma",   "Dr. Sunita Verma",
        "Prof. Amandeep Singh",        "Dr. Priya Nair",
        "Prof. Harpreet Kaur",         "Dr. Vikram Bhatia",
        "Prof. Neha Gupta",            "Dr. Gurpreet Singh Walia",
        "Prof. Sonal Chaudhary",       "Dr. Mandeep Kaur",
        "Prof. Rohit Bansal",          "Dr. Anjali Sharma",
        "Prof. Sandeep Arora",         "Dr. Ramandeep Singh",
        "Prof. Iqbal Singh",           "Dr. Meenakshi Sharma",
        "Prof. Tarun Khanna",          "Dr. Naveen Aggarwal",
        "Prof. Ritu Sharma",           "Dr. Deepak Garg",
    ],
    "ECE":  [
        "Prof. Deepak Bagai",          "Dr. Rekha Rani",
        "Prof. Jaswinder Singh",       "Dr. Nidhi Goel",
        "Prof. Ashok Kumar",           "Dr. Poonam Singla",
        "Prof. Tejinder Singh",        "Dr. Savita Gupta",
        "Prof. Monika Sharma",         "Dr. Rajneesh Talwar",
        "Prof. Anil Mittal",           "Dr. Seema Verma",
    ],
    "MEE":  [
        "Dr. Suresh Mehta",            "Prof. Balwinder Singh",
        "Dr. Kavita Sharma",           "Prof. Gurinder Singh",
        "Dr. Harish Pal",              "Prof. Inderpreet Arora",
        "Dr. Satish Kumar",            "Prof. Lakhwinder Singh",
        "Dr. Rajesh Khanna",           "Prof. Vinod Singhal",
    ],
    "CHE":  [
        "Prof. Ritu Mehta",            "Dr. Pankaj Agarwal",
        "Prof. Simran Kaur",           "Dr. Anupam Dikshit",
        "Prof. Beena Rani",            "Dr. Sunil Sharma",
        "Prof. Mohan Lal",             "Dr. Pratibha Singh",
    ],
    "CIE":  [
        "Prof. Amrinder Singh",        "Dr. Pooja Khanna",
        "Prof. Navneet Sharma",        "Dr. Lakhvir Singh",
        "Prof. Sushil Kumari",         "Dr. Rajiv Bansal",
        "Prof. Harbhajan Singh",       "Dr. Neelam Rani",
        "Prof. Gurmail Singh",         "Dr. Monika Aggarwal",
    ],
    "ELE":  [
        "Dr. Paramjit Kaur",           "Prof. Vivek Sharma",
        "Dr. Harmeet Singh",           "Prof. Mamta Rani",
        "Dr. Kulbir Singh",            "Prof. Satinder Kaur",
        "Dr. Balraj Singh",            "Prof. Neeraj Sharma",
        "Dr. Jaspal Kaur",             "Prof. Ravinder Kumar",
    ],
    "AIML": [
        "Dr. Satvir Singh",            "Prof. Anand Sharma",
        "Dr. Kamaldeep Kaur",          "Prof. Rajan Vohra",
        "Dr. Preethi Jyothi",          "Prof. Chirag Patel",
        "Dr. Nitin Saluja",            "Prof. Shruti Aggarwal",
        "Dr. Mohit Bajaj",             "Prof. Anu Shukla",
        "Dr. Suman Lata",              "Prof. Vaibhav Bhatia",
    ],
    "ENC":  [
        "Dr. Gurjit Kaur",             "Prof. Hardeep Singh",
        "Dr. Navdeep Kaur",            "Prof. Manish Bansal",
        "Dr. Parveen Kumar",           "Prof. Simranjit Kaur",
        "Dr. Tarsem Singh",            "Prof. Usha Kiran",
        "Dr. Vishal Goyal",            "Prof. Waqar Ahmed",
        "Dr. Yogesh Sharma",           "Prof. Zara Khan",
        "Dr. Arshdeep Singh",          "Prof. Bhupinder Kaur",
        "Dr. Chetan Arora",            "Prof. Dilpreet Kaur",
    ],
}


def _sem_for_year(year: int, sem_within_year: int) -> int:
    """
    Convert (year, semester_within_year) to global semester number.
    year=1, sem=1 → 1
    year=1, sem=2 → 2
    year=2, sem=1 → 3  … etc.
    """
    return (year - 1) * settings.SEMESTERS_PER_YEAR + sem_within_year


def _per_year_size(dept: str) -> int:
    """Students per year = annual intake ÷ academic years."""
    return settings.intake_map[dept] // settings.ACADEMIC_YEARS


def _needs_split(dept: str) -> bool:
    return _per_year_size(dept) > settings.SECTION_SPLIT_THRESHOLD


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Wipe existing data ────────────────────────────────────────────
        deleted_tt  = db.query(TimetableEntry).delete()
        deleted_sub = db.query(Subject).delete()
        deleted_bat = db.query(Batch).delete()
        deleted_rom = db.query(Room).delete()
        deleted_tea = db.query(Teacher).delete()
        db.commit()
        print(
            f"Cleared — {deleted_tea} teachers, {deleted_rom} rooms, "
            f"{deleted_bat} batches, {deleted_sub} subjects, "
            f"{deleted_tt} timetable entries."
        )

        active_depts = settings.active_department_list

        # ── Teachers ──────────────────────────────────────────────────────
        all_teachers: dict[str, list[Teacher]] = {}
        total_teacher_count = 0
        for dept in active_depts:
            pool = TEACHER_POOL[dept]
            dept_teachers = [Teacher(name=n, department=dept) for n in pool]
            db.add_all(dept_teachers)
            db.flush()
            all_teachers[dept] = dept_teachers
            total_teacher_count += len(dept_teachers)
        print(f"Added {total_teacher_count} teachers across {len(active_depts)} departments.")

        # ── Rooms ─────────────────────────────────────────────────────────
        room_spec = [
            ("A-LH", settings.ROOMS_300, 300),
            ("B-LH", settings.ROOMS_180, 180),
            ("C-SR", settings.ROOMS_120, 120),
            ("D-TR", settings.ROOMS_60,   60),
            ("E-CL", settings.ROOMS_40,   40),
            ("F-EL", settings.ROOMS_30,   30),
            ("G-ML", settings.ROOMS_25,   25),
        ]
        all_rooms = []
        for prefix, count, cap in room_spec:
            for i in range(1, count + 1):
                all_rooms.append(Room(name=f"{prefix}{i}", capacity=cap))
        db.add_all(all_rooms)
        db.flush()
        print(f"Added {len(all_rooms)} rooms.")

        # ── Batches ───────────────────────────────────────────────────────
        all_batches: dict[str, dict[int, list[Batch]]] = {}
        # all_batches[dept][year] = list of Batch objects (1 or 2 sections)
        total_batch_count = 0

        for dept in active_depts:
            all_batches[dept] = {}
            per_year = _per_year_size(dept)
            split    = _needs_split(dept)

            for year in range(1, settings.ACADEMIC_YEARS + 1):
                if split:
                    section_size = per_year // 2
                    batches = [
                        Batch(name=f"{dept}-Y{year}-A", department=dept,
                              size=section_size, year=year),
                        Batch(name=f"{dept}-Y{year}-B", department=dept,
                              size=section_size, year=year),
                    ]
                else:
                    batches = [
                        Batch(name=f"{dept}-Y{year}", department=dept,
                              size=per_year, year=year),
                    ]
                db.add_all(batches)
                db.flush()
                all_batches[dept][year] = batches
                total_batch_count += len(batches)

        print(f"Added {total_batch_count} batches.")

        # ── Subjects ──────────────────────────────────────────────────────
        # For each dept → each year → each semester-within-year → each batch section
        # assign SUBJECTS_PER_BATCH_PER_SEMESTER subjects, cycling through the
        # teacher pool round-robin per dept.
        #
        # We use only the first SUBJECTS_PER_BATCH_PER_SEMESTER entries from
        # the curriculum list for each semester, so increasing the env var
        # simply picks up more pre-defined subjects without code changes.

        n_subjects = settings.SUBJECTS_PER_BATCH_PER_SEMESTER
        lpw_core   = settings.LECTURES_PER_WEEK_CORE
        lpw_elec   = settings.LECTURES_PER_WEEK_ELECTIVE

        all_subjects = []
        teacher_idx: dict[str, int] = {dept: 0 for dept in active_depts}

        for dept in active_depts:
            dept_teachers = all_teachers[dept]
            curriculum    = CURRICULUM[dept]

            for year in range(1, settings.ACADEMIC_YEARS + 1):
                for sem_within_year in range(1, settings.SEMESTERS_PER_YEAR + 1):
                    global_sem   = _sem_for_year(year, sem_within_year)
                    sem_subjects = curriculum[global_sem][:n_subjects]
                    batches      = all_batches[dept][year]

                    for batch in batches:
                        for subj_name, subj_type in sem_subjects:
                            # Assign teacher round-robin within dept pool
                            teacher = dept_teachers[teacher_idx[dept] % len(dept_teachers)]
                            teacher_idx[dept] += 1

                            lpw = lpw_core if subj_type == "core" else lpw_elec
                            all_subjects.append(Subject(
                                name              = subj_name,
                                subject_type      = subj_type,
                                semester          = global_sem,
                                lectures_per_week = lpw,
                                teacher_id        = teacher.id,
                                batch_id          = batch.id,
                            ))

        db.add_all(all_subjects)
        db.commit()
        print(f"Added {len(all_subjects)} subjects.")

        # ── Summary ───────────────────────────────────────────────────────
        total_students  = sum(
            b.size
            for dept_batches in all_batches.values()
            for year_batches in dept_batches.values()
            for b in year_batches
        )
        total_lectures  = sum(s.lectures_per_week for s in all_subjects)
        total_semesters = settings.ACADEMIC_YEARS * settings.SEMESTERS_PER_YEAR

        print(f"\n{'=' * 62}")
        print(f"  TIET Patiala — Full {total_semesters}-Semester Seed Complete")
        print(f"{'=' * 62}")
        print(f"  Departments      : {len(active_depts)}  ({', '.join(active_depts)})")
        print(f"  Teachers         : {total_teacher_count}")
        print(f"  Rooms            : {len(all_rooms)}")
        print(f"  Batches          : {total_batch_count}  (sections included)")
        print(f"  Subjects total   : {len(all_subjects)}  ({n_subjects}/batch/sem)")
        print(f"  Students (seats) : {total_students:,}")
        print(f"  Lectures/week    : {total_lectures}  (all semesters combined)")
        print(f"{'=' * 62}")
        print(f"\n  Dept breakdown:")
        for dept in active_depts:
            n_bat = sum(len(v) for v in all_batches[dept].values())
            n_tea = len(all_teachers[dept])
            split_note = " (split A+B)" if _needs_split(dept) else ""
            print(f"    {dept:<6} : {n_bat:>3} batches, {n_tea:>3} teachers{split_note}")
        print(f"\n  Run:  POST /generate-timetable/{{semester}}  (1–{total_semesters})")
        print(f"  E.g.: POST /generate-timetable/1   → schedules Semester 1 only")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()