import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ================= FILE PATHS =================
DATA_JSON = "map/data/rap_unified_dataset.json"
OUTPUT_JSON = "map/data/lr_coefficients.json"

# ================= LOAD DATA =================
with open(DATA_JSON, "r") as f:
    data = json.load(f)

samples = data["samples"]

X = np.array([[s["cape"], s["cin"], s["hlcy"]] for s in samples])
y = np.array([s["tornado"] for s in samples])

print("X shape:", X.shape)
print("y shape:", y.shape)
print("Number of tornado samples:", y.sum())
print("Number of non-tornado samples:", len(y) - y.sum())

# ================= STANDARDIZE FEATURES =================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ================= LOGISTIC REGRESSION =================
lr = LogisticRegression(class_weight='balanced', solver='lbfgs', max_iter=1000)
lr.fit(X_scaled, y)

# ================= SAVE COEFFICIENTS =================
coefficients = lr.coef_[0]
intercept = lr.intercept_[0]

coef_output = {
    "features": ["cape", "cin", "hlcy"],
    "coefficients": coefficients.tolist(),
    "intercept": float(intercept)
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(coef_output, f, indent=2)

# ================= PRINT =================
print("\n=== Logistic Regression Coefficients ===")
for name, coef in zip(coef_output["features"], coef_output["coefficients"]):
    print(f"{name}: {coef:.8f}")
print(f"Intercept: {coef_output['intercept']:.8f}")
print("\nSaved coefficients to:", OUTPUT_JSON)
