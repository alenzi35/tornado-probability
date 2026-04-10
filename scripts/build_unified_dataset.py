```python
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# ================= FILE PATHS =================

TORNADO_CSV = "map/data/rap_tornado_samples.csv"
NON_TORNADO_CSV = "map/data/rap_non_tornado_samples.csv"

# ================= LOAD DATA =================

print("Loading datasets...")

tor = pd.read_csv(TORNADO_CSV)
non_tor = pd.read_csv(NON_TORNADO_CSV)

print(f"Tornado samples: {len(tor)}")
print(f"Non-tornado samples: {len(non_tor)}")

# Combine
data = pd.concat([tor, non_tor], ignore_index=True)

print(f"Total samples: {len(data)}")

# ================= CLEAN DATA =================

# Drop any NaNs just in case
data = data.replace([np.inf, -np.inf], np.nan)
data = data.dropna()

print(f"Samples after cleaning: {len(data)}")

# ================= OPTIONAL FILTER (HIGH IMPACT) =================
# Only keep storm-capable environments

data = data[(data["cape"] > 100) & (data["hlcy"] > 50)]

print(f"Samples after environment filter: {len(data)}")

# ================= FEATURES =================

features = [
    "cape",
    "cin",
    "hlcy",
    "lcl",
    "shear"
]

X = data[features]
y = data["tornado"]

# ================= NORMALIZE =================

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ================= TRAIN MODEL =================

print("\nTraining logistic regression...")

model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced"
)

model.fit(X_scaled, y)

# ================= OUTPUT RESULTS =================

print("\n===== MODEL RESULTS =====")

print("\nIntercept:")
print(model.intercept_[0])

print("\nCoefficients:")
for name, coef in zip(features, model.coef_[0]):
    print(f"{name}: {coef}")

# ================= MODEL SKILL =================

probs = model.predict_proba(X_scaled)[:, 1]
auc = roc_auc_score(y, probs)

print("\nAUC Score:", auc)

print("\nDONE.")
```
