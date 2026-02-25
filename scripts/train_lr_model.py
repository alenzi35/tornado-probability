import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ================= LOAD DATA =================
DATA_JSON = "map/data/rap_unified_dataset.json"

with open(DATA_JSON, "r") as f:
    data = json.load(f)

samples = data["samples"]

# Extract features and labels
X = np.array([[s["cape"], s["cin"], s["hlcy"]] for s in samples])
y = np.array([s["tornado"] for s in samples])

print("X shape:", X.shape)
print("y shape:", y.shape)
print("Number of tornado samples:", y.sum())
print("Number of non-tornado samples:", len(y) - y.sum())

# ================= OPTIONAL: STANDARDIZE FEATURES =================
# Scaling improves convergence
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ================= LOGISTIC REGRESSION =================
# Use class_weight='balanced' because dataset is highly imbalanced
lr = LogisticRegression(class_weight='balanced', solver='lbfgs', max_iter=1000)
lr.fit(X_scaled, y)

# ================= RESULTS =================
print("\n=== Logistic Regression Coefficients ===")
coefficients = lr.coef_[0]
intercept = lr.intercept_[0]

for name, coef in zip(["cape", "cin", "hlcy"], coefficients):
    print(f"{name}: {coef:.8f}")

print(f"Intercept: {intercept:.8f}")

# ================= OPTIONAL: SAVE MODEL COEFFICIENTS =================
import pickle
with open("map/data/lr_model.pkl", "wb") as f:
    pickle.dump({
        "scaler": scaler,
        "coefficients": coefficients,
        "intercept": intercept
    }, f)

print("\nModel saved to map/data/lr_model.pkl")
