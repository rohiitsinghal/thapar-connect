"""
main.py
Entry point for the TSLAS Timetable Scheduler.

Project structure:
  backend_new/
  ├── data/
  │   ├── software_files.xlsx
  │   └── rooms.xlsx
  ├── output/
  │   ├── extracted_data.json
  │   └── timetable.json
  ├── extractor.py
  ├── scheduler.py
  └── main.py

Usage:
  cd backend_new
  python main.py
"""

import os
from extractor import load_data
from genMaster import build_master, load_timetable
from scheduler import run

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SOFTWARE_XLSX  = os.path.join(DATA_DIR,   "software_files.xlsx")
ROOMS_XLSX     = os.path.join(DATA_DIR,   "rooms.xlsx")
EXTRACTED_JSON = os.path.join(OUTPUT_DIR, "extracted_data.json")
TIMETABLE_JSON = os.path.join(OUTPUT_DIR, "timetable.json")
MASTER_TIMETABLE_XLSX = os.path.join(OUTPUT_DIR, "master_timetable.xlsx")

# ─────────────────────────────────────────────────────────────────────────────
# *** SET THIS BEFORE EVERY RUN ***
#
# "even" → schedules semesters 2, 4, 6   (runs during even semester period)
# "odd"  → schedules semesters 1, 3, 5   (runs during odd semester period)
# ─────────────────────────────────────────────────────────────────────────────

ACTIVE_PARITY = "even"

# ─────────────────────────────────────────────────────────────────────────────
# SA parameters
#
# These were re-tuned for the v3 unit-based scheduler (242+ schedulable
# units, 6000+ conflict edges — much larger search space than the old
# course_code-based v2 scheduler). The previous v2 params (initial_temp
# 50000, cooling_rate 0.9997) caused runs of 30-40+ minutes because the
# stopping condition incorrectly compared TOTAL penalty (hard + soft)
# against a fixed threshold. Soft penalties (room capacity, teacher load,
# day-spread) routinely sit in the tens of thousands even on a perfectly
# valid timetable, so that comparison could never succeed and the loop
# ran until cooling bottomed out — never confirming hard constraints
# were actually already satisfied.
#
# Fixed in scheduler.py: hard and soft penalties are now tracked
# SEPARATELY. The SA loop stops as soon as hard penalty == 0 (zero
# student/teacher/room/practical-placement violations), then runs a
# short "polish" pass to reduce soft penalty without ever reintroducing
# a hard violation.
#
# With a real run (242 units, 6114 conflict edges) this configuration
# reaches zero hard violations in under 1 second (often instantly from
# the greedy initial construction alone) and finishes the soft-penalty
# polish pass in well under a minute total.
# ─────────────────────────────────────────────────────────────────────────────

SA_PARAMS = {
    "initial_temp":      3000.0,    # lower — greedy start is already decent
    "cooling_rate":      0.997,     # moderate cooling, enough steps to refine
    "min_temp":          0.5,
    "iters_per_temp":    60,
    "restart_threshold": 800,
    "polish_iters":      20000,     # extra soft-penalty refinement after
                                     # hard constraints are satisfied
}


def generate_timetable(active_parity=ACTIVE_PARITY, sa_params=None):
    if active_parity not in ("even", "odd"):
        raise ValueError(f"ACTIVE_PARITY must be 'even' or 'odd', got '{active_parity}'")

    selected_sa_params = dict(SA_PARAMS)
    if sa_params:
        selected_sa_params.update(sa_params)

    active_sems = [2, 4, 6] if active_parity == "even" else [1, 3, 5]

    load_data(
        software_xlsx=SOFTWARE_XLSX,
        rooms_xlsx=ROOMS_XLSX,
        output_json=EXTRACTED_JSON,
        active_semesters=active_sems,
    )

    run(
        extracted_json=EXTRACTED_JSON,
        output_json=TIMETABLE_JSON,
        **selected_sa_params,
    )

    timetable = load_timetable(TIMETABLE_JSON)
    build_master(timetable, MASTER_TIMETABLE_XLSX)
    return timetable


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Validate parity setting
    if ACTIVE_PARITY not in ("even", "odd"):
        print(f"\n  ✗ ERROR: ACTIVE_PARITY must be 'even' or 'odd', got '{ACTIVE_PARITY}'\n")
        raise SystemExit(1)

    # Validate input files exist
    for path, label in [(SOFTWARE_XLSX, "software_files.xlsx"),
                        (ROOMS_XLSX,    "rooms.xlsx")]:
        if not os.path.exists(path):
            print(f"\n  ✗ ERROR: Cannot find '{label}' at:\n    {path}")
            print(f"  Make sure both Excel files are in the data/ folder.\n")
            raise SystemExit(1)

    active_sems = [2, 4, 6] if ACTIVE_PARITY == "even" else [1, 3, 5]
    print(f"\n  Running for {ACTIVE_PARITY.upper()} semesters: {active_sems}")

    # Step 1 — Extract
    print("\n" + "─" * 65)
    print("  STEP 1 — EXTRACT DATA FROM EXCEL")
    print("─" * 65)
    generate_timetable(ACTIVE_PARITY)

    print("\n" + "=" * 65)
    print("  ALL DONE")
    print("=" * 65)
    print(f"  Parity          : {ACTIVE_PARITY.upper()}  {active_sems}")
    print(f"  extracted_data  : {EXTRACTED_JSON}")
    print(f"  timetable       : {TIMETABLE_JSON}")
    print()
    print("  Query timetable:")
    print("    timetable['by_student']['1424000018']  → personal timetable")
    print("    timetable['by_day']['Monday']           → all Monday classes")
    print("    timetable['timetable']                  → all classes flat")
    print("    master_timetable.xlsx                    → generated master spreadsheet")
    print()
    print("  Run python test.py afterwards to verify zero clashes.")
    print("=" * 65)