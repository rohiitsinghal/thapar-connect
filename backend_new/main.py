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

# ─────────────────────────────────────────────────────────────────────────────
# *** SET THIS BEFORE EVERY RUN ***
#
# "even" → schedules semesters 2, 4, 6   (runs during even semester period)
# "odd"  → schedules semesters 1, 3, 5   (runs during odd semester period)
# ─────────────────────────────────────────────────────────────────────────────

ACTIVE_PARITY = "even"

# ─────────────────────────────────────────────────────────────────────────────
# SA parameters
# ─────────────────────────────────────────────────────────────────────────────

SA_PARAMS = {
    "initial_temp":      50000.0,
    "cooling_rate":      0.9997,
    "min_temp":          1.0,
    "iters_per_temp":    100,
    "restart_threshold": 3000,
}


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
    load_data(
        software_xlsx  = SOFTWARE_XLSX,
        rooms_xlsx     = ROOMS_XLSX,
        output_json    = EXTRACTED_JSON,
        active_semesters = active_sems,
    )

    # Step 2 — Schedule
    print("\n" + "─" * 65)
    print(f"  STEP 2 — SCHEDULE  ({ACTIVE_PARITY.upper()} semesters: {active_sems})")
    print("─" * 65)
    run(
        extracted_json = EXTRACTED_JSON,
        output_json    = TIMETABLE_JSON,
        **SA_PARAMS,
    )

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
    print("=" * 65)