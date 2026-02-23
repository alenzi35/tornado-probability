import json
import random
from pathlib import Path
import subprocess
import sys

# =========================
# CONFIG — EDIT THESE ONLY
# =========================

# 4 RAP analysis snapshots (NO forecast hour)
# Format: (YYYYMMDD, HH)
SNAPSHOTS = [
    ("20250724", "14"),
    ("20250915", "17"),
    ("20250921", "20"),
    ("20251230", "23"),
]

TORNADO_FILE = Path("data/tornado_samples.json")

OUTPUT_FILE = Path("data/dataset.json")

TEMP_FILE = Path("data/rap_grid.json")


# =========================
# FUNCTIONS
# =========================

def run_process_rap(date, hour):

    print(f"Processing RAP analysis: {date} {hour}z")

    cmd = [
        sys.executable,
        "scripts/process_rap.py",
        date,
        hour
    ]

    subprocess.run(cmd, check=True)

    if not TEMP_FILE.exists():
        raise RuntimeError("process_rap.py did not produce rap_grid.json")

    with open(TEMP_FILE) as f:
        data = json.load(f)

    return data


def label_non_tornado(samples):

    return [
        {
            "mlcape": s["mlcape"],
            "mlcin": s["mlcin"],
            "srh01": s["srh01"],
            "label": 0
        }
        for s in samples
    ]


def load_tornado_samples():

    print("Loading tornado samples...")

    with open(TORNADO_FILE) as f:
        tors = json.load(f)

    return [
        {
            "mlcape": s["mlcape"],
            "mlcin": s["mlcin"],
            "srh01": s["srh01"],
            "label": 1
        }
        for s in tors
    ]


# =========================
# MAIN
# =========================

def main():

    dataset = []

    # NON-TORNADO
    for date, hour in SNAPSHOTS:

        samples = run_process_rap(date, hour)

        samples = label_non_tornado(samples)

        dataset.extend(samples)

        print(f"Added {len(samples)} non-tornado samples")


    # TORNADO
    tornado_samples = load_tornado_samples()

    dataset.extend(tornado_samples)

    print(f"Added {len(tornado_samples)} tornado samples")


    # SHUFFLE
    random.shuffle(dataset)

    print(f"Final dataset size: {len(dataset)}")


    # SAVE
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(dataset, f)

    print(f"Saved dataset → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
