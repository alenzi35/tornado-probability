import pandas as pd
from sklearn.linear_model import LogisticRegression

# ================= LOAD DATA =================

tornado = pd.read_csv("map/data/rap_tornado_samples.csv")
non_tornado = pd.read_csv("map/data/rap_non_tornado_samples.csv")

data = pd.concat([tornado, non_tornado], ignore_index=True)

print("Total samples:", len(data))
print("Tornado samples:", data["tornado"].sum())
print("Non-tornado samples:", len(data) - data["tornado"].sum())

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

# ================= DEBUG: FEATURE STATS =================

print("\n================ FEATURE RANGES ================")
print(X.describe())

print("\n================ SAMPLE TORNADO ROWS ================")
print(data[data["tornado"] == 1][features].head())

print("\n================ SAMPLE NON-TORNADO ROWS ================")
print(data[data["tornado"] == 0][features].head())

# ================= TRAIN LR =================

model = LogisticRegression(max_iter=1000)

model.fit(X, y)

# ================= RESULTS =================

print("\n================ MODEL OUTPUT ================")

print("\nIntercept:")
print(model.intercept_[0])

print("\nCoefficients:")

for name, coef in zip(features, model.coef_[0]):
    print(name, coef)
