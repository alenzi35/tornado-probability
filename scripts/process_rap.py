import json
import numpy as np
import xarray as xr
from math import exp

# ===============================
# MANUAL DATE FOR TESTING
# ===============================
RUN_DATE = "20240506"   # change whenever you want
RUN_HOUR = "21"         # 00,06,12,18 etc

# ===============================
# LOGISTIC REGRESSION COEFFICIENTS
# ===============================
COEFFICIENTS = {
    "CAPE": 0.0007852504286701655,
    "CIN": -0.003028035273017941,
    "HLCY": 0.008318690761993085
}

INTERCEPT_MANUAL = -11.9


# ===============================
# LOAD RAP FILE
# ===============================
rap_file = f"map/data/rap/{RUN_DATE}_{RUN_HOUR}.nc"

print("Loading RAP:", rap_file)

ds = xr.open_dataset(rap_file)


# ===============================
# READ VARIABLES
# ===============================
cape = ds["CAPE"].values
cin = ds["CIN"].values

# RAP uses HLCY (storm-relative helicity)
hlcy = ds["HLCY"].values


# grid coordinates
x_vals = ds["x"].values
y_vals = ds["y"].values

dx = float(x_vals[1] - x_vals[0])
dy = float(y_vals[1] - y_vals[0])


# ===============================
# LOGISTIC FUNCTION
# ===============================
def logistic(z):
    return 1 / (1 + exp(-z))


# ===============================
# BUILD FEATURES
# ===============================
features = []

for j, y in enumerate(y_vals):
    for i, x in enumerate(x_vals):

        cape_val = float(cape[j, i])
        cin_val = float(cin[j, i])
        hlcy_val = float(hlcy[j, i])

        # logistic regression
        z = (
            INTERCEPT_MANUAL
            + COEFFICIENTS["CAPE"] * cape_val
            + COEFFICIENTS["CIN"] * cin_val
            + COEFFICIENTS["HLCY"] * hlcy_val
        )

        prob = logistic(z)

        features.append({
            "x": float(x),
            "y": float(y),
            "dx": dx,
            "dy": dy,
            "prob": float(prob),

            # environmental fields for tooltip
            "CAPE": cape_val,
            "CIN": cin_val,
            "SRH": hlcy_val
        })


# ===============================
# OUTPUT JSON
# ===============================
output = {
    "type": "FeatureCollection",
    "run_date": RUN_DATE,
    "run_hour": RUN_HOUR,
    "forecast": "F01",
    "features": features
}

out_file = "map/data/tornado_prob_lcc.json"

with open(out_file, "w") as f:
    json.dump(output, f)

print("Saved:", out_file)
print("Cells:", len(features))
