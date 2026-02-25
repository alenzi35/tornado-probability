import os
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# ================= PATH CONFIG =================
# Determine repo root dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths to your data
UNIFIED_JSON = os.path.join(BASE_DIR, "map", "data", "rap_unified_dataset.json")
TORNADO_CSV = os.path.join(BASE_DIR, "map", "data", "tornado_samples.csv")

print("Looking for non-tornado JSON at:", UNIFIED_JSON)
print("Looking for tornado CSV at:", TORNADO_CSV)

# ================= CHECK FILE EXISTENCE =================
if not os.path.isfile(UNIFIED_JSON):
    raise FileNotFoundError(f"Non-tornado JSON not found at {UNIFIED_JSON}")

if not os.path.isfile(TORNADO_CSV):
    raise FileNotFoundError(f"Tornado CSV not found at {TORNADO_CSV}")

# ================= LOAD NON-TORNADO =================
with open(UNIFIED_JSON, "r") as f:
    data = json.load(f)

print("File loaded. Top-level keys:", list(data.keys()))

non_tornado = []

# Multi-snapshot format
if "snapshots" in data:
    for snap in data["snapshots"]:
        for feat in snap["features"]:
            non_tornado.append([
                feat["cape"],
                feat["cin"],
                feat["hlcy"],
                0  # label = non-tornado
            ])
else:
    raise ValueError("JSON format not recognized. Must contain 'snapshots'.")

non_tornado = np.array(non_tornado)
print("Loaded non-tornado samples:", len(non_tornado))

# ================= LOAD TORNADO =================
tor_df = pd.read_csv(TORNADO_CSV)

tornado = np.column_stack([
    tor_df["mlcape"].values,
    tor_df["mlcin"].values,
    tor_df["srh01"].values,
    np.ones(len(tor_df))  # label = tornado
])
print("Loaded tornado samples:", len(tornado))

# ================= COMBINE DATA =================
all_data = np.vstack([non_tornado, tornado])
X = all_data[:, 0:3]  # CAPE, CIN, HLCY
y = all_data[:, 3]    # labels

print("Total samples:", len(y))
print("Empirical tornado rate:", np.mean(y))

# ================= TRAIN LOGISTIC REGRESSION =================
model = LogisticRegression(max_iter=10000, solver="lbfgs")
model.fit(X, y)

print("\n===== RAW MODEL COEFFICIENTS =====")
print("CAPE:", model.coef_[0][0])
print("CIN :", model.coef_[0][1])
print("HLCY:", model.coef_[0][2])
print("Intercept:", model.intercept_[0])
print("==================================")
