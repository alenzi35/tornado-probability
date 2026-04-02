import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# ================= LOAD DATA =================

tornado = pd.read_csv("map/data/rap_tornado_samples.csv")
non_tornado = pd.read_csv("map/data/rap_non_tornado_samples.csv")

df = pd.concat([tornado, non_tornado], ignore_index=True)

print("Total samples:", len(df))
print("Tornado samples:", df["tornado"].sum())

# ================= FEATURES =================

features = [
    "cape",
    "cin",
    "hlcy",
    "lcl",
    "shear"
]

X = df[features]
y = df["tornado"]

# ================= TRAIN TEST SPLIT =================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ================= TRAIN MODEL =================

model = LogisticRegression(max_iter=1000)

model.fit(X_train, y_train)

# ================= EVALUATE =================

pred = model.predict_proba(X_test)[:,1]

auc = roc_auc_score(y_test, pred)

print("\nAUC:", auc)

# ================= PRINT EQUATION =================

print("\nLogistic Regression Equation\n")

print("Intercept =", model.intercept_[0])

for name, coef in zip(features, model.coef_[0]):
    print(f"{name}: {coef}")
