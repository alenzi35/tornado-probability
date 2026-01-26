#!/usr/bin/env python3
import os
import urllib.request
import pygrib
import numpy as np
import json

# -------------------------------
# 1️⃣ RAP GRIB URL
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
# 4️⃣ Safe fuzzy variable picker
def pick_variable_fuzzy(grbs, varname_keywords):
    """
    Pick the first GRIB message whose shortName, name, or description
    contains any of the keywords (case-insensitive).
    Safely handles missing keys.
    """
    varname_keywords = [k.lower() for k in varname_keywords]

    for g in grbs:
        # Only check keys that exist
        fields_to_check = []
        for key in ['shortName', 'name', 'description']:
            if key in g.keys():  # safe access
                fields_to_check.append(str(g[key]).lower())

        if any(any(k in f for f in fields_to_check) for k in varname_keywords):
            level = g['level'] if 'level' in g.keys() else 'unknown'
            typel = g['typeOfLevel'] if 'typeOfLevel' in g.keys() else 'unknown'
            print(f"✅ Found {varname_keywords[0]}: level {level} ({typel})")
            return g

    raise RuntimeError(f"❌ None of the keywords {varname_keywords} found in GRIB")

# -------------------------------
# 5️⃣ Pick variables using fuzzy names
CAPE_msg = pick_variable_fuzzy(grbs, ["cape"])
CIN_msg  = pick_variable_fuzzy(grbs, ["cin", "convectiveinhibition"])
HLCY_msg = pick_variable_fuzzy(grbs, ["hlcy", "stormrelativehelicity"])

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
# 8️⃣ Build JSON for map
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
