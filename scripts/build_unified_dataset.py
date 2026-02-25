import json
import pandas as pd

# ================= FILE PATHS =================

NON_TOR_JSON = "map/data/rap_non_tornado_snapshots.json"
TORNADO_CSV = "data/tornado_samples.csv"
OUTPUT_JSON = "map/data/rap_unified_dataset.json"

# ================= LOAD NON-TORNADO DATA =================

print("Loading non-tornado snapshots...")

with open(NON_TOR_JSON, "r") as f:
    non_tor_data = json.load(f)

samples = []

for snapshot in non_tor_data["snapshots"]:
    for feature in snapshot["features"]:
        samples.append({
            "cape": feature["cape"],
            "cin": feature["cin"],
            "hlcy": feature["hlcy"],
            "tornado": 0
        })

print(f"Loaded {len(samples)} non-tornado samples.")

# ================= LOAD TORNADO CSV =================

print("Loading tornado CSV...")

tornado_df = pd.read_csv(TORNADO_CSV)

print(f"Loaded {len(tornado_df)} tornado samples.")

for _, row in tornado_df.iterrows():
    samples.append({
        "cape": float(row["mlcape"]),
        "cin": float(row["mlcin"]),
        "hlcy": float(row["srh01"]),
        "tornado": 1
    })

# ================= SAVE UNIFIED DATASET =================

output = {
    "total_samples": len(samples),
    "tornado_count": int((tornado_df.shape[0])),
    "non_tornado_count": len(samples) - tornado_df.shape[0],
    "samples": samples
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("\nUnified dataset saved to:", OUTPUT_JSON)
print("Total samples:", output["total_samples"])
print("Tornado samples:", output["tornado_count"])
print("Non-tornado samples:", output["non_tornado_count"])
print("DONE.")
