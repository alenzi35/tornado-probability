import json
import pandas as pd
import os

# ================= FILE PATHS =================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TORNADO_CSV = os.path.join(BASE_DIR, "map", "data", "1hr_samples.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "map", "data", "rap_unified_dataset.json")

print("Looking for tornado CSV at:", TORNADO_CSV)

# ================= CHECK FILE =================

if not os.path.isfile(TORNADO_CSV):
    raise FileNotFoundError(f"Tornado CSV not found at {TORNADO_CSV}")

# ================= LOAD CSV =================

print("Loading tornado CSV...")

tornado_df = pd.read_csv(TORNADO_CSV)

print(f"Loaded {len(tornado_df)} tornado samples.")

# ================= BUILD DATASET =================

samples = []

for _, row in tornado_df.iterrows():

    sample = {
        "cape": float(row["CAPE"]),
        "cin": float(row["CIN"]),
        "srh": float(row["SRH"]),
        "lcl": float(row["LCL"]),
        "shear": float(row["Shear"]),
        "tornado": 1
    }

    samples.append(sample)

# ================= SAVE UNIFIED DATASET =================

output = {
    "total_samples": len(samples),
    "tornado_count": len(samples),
    "non_tornado_count": 0,
    "samples": samples
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("\nUnified dataset saved to:", OUTPUT_JSON)
print("Total samples:", output["total_samples"])
print("Tornado samples:", output["tornado_count"])
print("Non-tornado samples:", output["non_tornado_count"])
print("DONE.")
