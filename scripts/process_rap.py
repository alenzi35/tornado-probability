#!/usr/bin/env python3
import os
import urllib.request
import pygrib
import numpy as np
import json

# -------------------------------
# 1️⃣ RAP GRIB URL
# Adjust date/time as needed
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
# 3️⃣ Coefficients for 1-hour probability
intercept = -1.5686
coeffs = {"CAPE": 0.0028859237, "CIN": 2.38728498e-05, "HLCY": 0.00885192696}

# -------------------------------
# 4️⃣ Robust variable picker
def pick_variable(grbs, varname, candidate_levels):
    varname_lc = varname.lower()
    msgs = [g for g in grbs if g.shortName.lower() == varname_lc]

    for lvl in candidate_levels:
        for m in msgs:
            if getattr(m, "typeOfLevel", "") == lvl:
                print(f"{varname}: using level {getattr(m,'level','unknown')} ({lvl})")
                return m

    # fallback: first available message
    if msgs:
        print(f"{varname}: using first available level {getattr(msgs[0],'level','unknown')} ({getattr(msgs[0],'typeOfLevel','unknown')})")
        return msgs[0]

    raise RuntimeError(f"{varname} NOT FOUND in GRIB!")

# -------------------------------
# 5️⃣ Pick variables (fallbacks)
CAPE_msg = pick_variable(grbs, "CAPE", ["pressureFromGroundLayer", "surface"])
CIN_msg  = pick_variable(grbs, "CIN", ["pressureFromGroundLayer", "surface"])
HLCY_msg = pick_variable(grbs, "HLCY", ["heightAboveGroundLayer"])

# -------------------------------
# 6️⃣ Extract arrays
CAPE = CAPE_msg.values
CIN  = CIN_msg.values
HLCY = HLCY_msg.values

lats, lons = CAPE_msg.latlons()  # grid coordinates

# -------------------------------
# 7️⃣ Compute 1-hour tornado probability
linear_comb = intercept + CAPE*coeffs["CAPE"] + CIN*coeffs["CIN"] + HLCY*coeffs["HLCY"]
prob = 1 / (1 + np.exp(-linear_comb))  # logistic function

# -------------------------------
# 8️⃣ Build JSON
cells = []
for i in range(prob.shape[0]):
    for j in range(prob.shape[1]):
        cells.append({
            "lat": float(lats[i,j]),
            "lon": float(lons[i,j]),
            "prob": float(prob[i,j])
        })

json_file = "data/tornado_prob.json"
with open(json_file, "w") as f:
    json.dump(cells, f)

print(f"✅ Tornado probability JSON saved to {json_file}")
