import json
import math
import os

INPUT = "data/dataset.json"
OUTPUT = "data/lr_model.json"

# ----------------------------
# Load dataset
# ----------------------------

with open(INPUT) as f:
    data = json.load(f)

X = []
y = []

for sample in data:
    X.append([
        sample["mlcape"],
        sample["mlcin"],
        sample["srh01"]
    ])
    y.append(sample["label"])

n = len(X)

print(f"Loaded {n} samples")

# ----------------------------
# Compute normalization params
# ----------------------------

means = [0, 0, 0]
stds = [0, 0, 0]

for j in range(3):
    means[j] = sum(X[i][j] for i in range(n)) / n

for j in range(3):
    stds[j] = math.sqrt(sum((X[i][j] - means[j])**2 for i in range(n)) / n)

print("Means:", means)
print("Stds:", stds)

# Normalize
Xn = []
for i in range(n):
    Xn.append([
        (X[i][0] - means[0]) / stds[0],
        (X[i][1] - means[1]) / stds[1],
        (X[i][2] - means[2]) / stds[2]
    ])

# ----------------------------
# Logistic regression training
# ----------------------------

weights = [0.0, 0.0, 0.0]
bias = 0.0

lr = 0.01
epochs = 5000

def sigmoid(z):
    return 1 / (1 + math.exp(-z))

for epoch in range(epochs):

    dw = [0, 0, 0]
    db = 0

    for i in range(n):

        z = (
            weights[0] * Xn[i][0] +
            weights[1] * Xn[i][1] +
            weights[2] * Xn[i][2] +
            bias
        )

        pred = sigmoid(z)
        error = pred - y[i]

        dw[0] += error * Xn[i][0]
        dw[1] += error * Xn[i][1]
        dw[2] += error * Xn[i][2]

        db += error

    # update
    weights[0] -= lr * dw[0] / n
    weights[1] -= lr * dw[1] / n
    weights[2] -= lr * dw[2] / n
    bias -= lr * db / n

    if epoch % 500 == 0:
        print(f"Epoch {epoch}")

# ----------------------------
# Save model
# ----------------------------

model = {
    "weights": weights,
    "bias": bias,
    "means": means,
    "stds": stds,
    "features": ["mlcape", "mlcin", "srh01"]
}

os.makedirs("data", exist_ok=True)

with open(OUTPUT, "w") as f:
    json.dump(model, f, indent=4)

print("\nTRAINING COMPLETE")
print("Weights:", weights)
print("Bias:", bias)
print(f"Saved model → {OUTPUT}")
