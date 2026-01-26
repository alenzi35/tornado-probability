#!/usr/bin/env python3
import pygrib
import numpy as np
import json
import os
import urllib.request

# -------------------------------
# 1️⃣ RAP GRIB URL (adjust date/time as needed)
# Example: Jan 26, 2026, 19Z + 2h forecast
rap_url = "https://noaa-rap-pds.s3.amazonaws.com/rap.20260126/rap.t19z.awp130pgrbf02.grib2"
local_file = "data/rap_latest.grib2"
os.makedirs("data", exist_ok=True)

# Download if not already present
if not os.path.exists(local_file):
    print(f"Downloading RAP GRIB from {rap_url} ...")
    urllib.request.urlretrieve(rap_url, local_file)
    print("Download complete.\n")

# -------------------------------
# 2️⃣ Open GRIB
grbs = pygrib.open(local_file)

# -------------------------------
# 3️⃣ Coefficients
intercept = -1.5686
coeffs = {"CAPE": 0.0028859237, "CIN": 2.38728498e-05, "HLCY": 0.00885192696}

# -------------------------------
# 4️⃣ Pick variables
def pick_variable(grbs, name, fallback_levels):
    msgs = [g for g in grbs if g.shortName==name]
    for lvl in fallback_levels:
        for m in msgs:
            if getattr(m, "typeOfLevel", "") == lvl:
                return m
    # fallback to first available
    if msgs:
        return msgs[0]
    raise RuntimeError(f"{name} NOT FOUND in GRIB!")

# For testing, we'll accept surface if exact levels not found
CAPE_msg = pick_variable(grbs, "CAPE", ["pressureFromGroundLayer", "surface"])
CIN_msg  = pick_variable(grbs, "CIN", ["pressureFromGroundLayer", "surface"])
HLCY_msg = pick_variable(grbs, "HLCY", ["heightAboveGroundLayer"])

# -------------------------------
# 5️⃣ Extract data as arrays
CAPE = CAPE_msg.values
CIN  = CIN_msg.values
HLCY = HLCY_msg.values

lats, lons = CAPE_msg.latlons()  # all variables on same grid

# -------------------------------
# 6️⃣ Compute 1-hour probability
linear_comb = intercept + CAPE*coeffs["CAPE"] + CIN*coeffs["CIN"] + HLCY*coeffs["HLCY"]
prob = 1 / (1 + np.exp(-linear_comb))

# -------------------------------
# 7️⃣ Build JSON
cells = []
for i in range(prob.shape[0]):
    for j in range(prob.shape[1]):
        cells.append({
            "lat": float(lats[i,j]),
            "lon": float(lons[i,j]),
            "prob": float(prob[i,j])
        })

with open("data/tornado_prob.json", "w") as f:
    json.dump(cells, f)

print("✅ Tornado probability JSON saved to data/tornado_prob.json")
