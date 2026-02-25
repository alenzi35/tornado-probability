import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

UNIFIED_JSON = "map/data/rap_unified_dataset.json"
TORNADO_CSV = "tornado_samples.csv"

# ---------- Load non-tornado ----------
with open(UNIFIED_JSON, "r") as f:
    data = json.load(f)

non_tornado = []

for snap in data["snapshots"]:
    for feat in snap["features"]:
        non_tornado.append([
            feat["cape"],
            feat["cin"],
            feat["hlcy"],
            0
        ])

non_tornado = np.array(non_tornado)

# ---------- Load tornado ----------
tor_df = pd.read_csv(TORNADO_CSV)

tornado = np.column_stack([
    tor_df["mlcape"].values,
    tor_df["mlcin"].values,
    tor_df["srh01"].values,
    np.ones(len(tor_df))
])

# ---------- Combine ----------
all_data = np.vstack([non_tornado, tornado])

X = all_data[:, 0:3]
y = all_data[:, 3]

print("Total samples:", len(y))
print("Tornado rate:", np.mean(y))

# ---------- Train Logistic Regression ----------
model = LogisticRegression(
    max_iter=10000,
    solver="lbfgs"
)

model.fit(X, y)

print("\n===== RAW MODEL COEFFICIENTS =====")
print("CAPE:", model.coef_[0][0])
print("CIN :", model.coef_[0][1])
print("HLCY:", model.coef_[0][2])
print("Intercept:", model.intercept_[0])
print("==================================")
