import os
import json
import numpy as np
import urllib.request
import pygrib

# =========================
# CONFIG
# =========================
DATE = "20260126"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awp130pgrbf{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

# Logistic regression coefficients (1-hour)
INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# =========================
# DOWNLOAD RAP
# =========================
os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete.")

# =========================
# OPEN GRIB
# =========================
grbs = pygrib.open(GRIB_PATH)

def find_var(grbs, shortname):
    for g in grbs:
        if g.shortName.lower() == shortname.lower():
            print(f"✅ Found {shortname}: level {g.level} ({g.typeOfLevel})")
            return g
    raise RuntimeError(f"{shortname} NOT FOUND in GRIB")

# =========================
# EXTRACT VARIABLES
# =========================
grbs.seek(0)
cape_msg = find_var(grbs, "cape")
grbs.seek(0)
cin_msg  = find_var(grbs, "cin")
grbs.seek(0)
hlcy_msg = find_var(grbs, "hlcy")

CAPE = cape_msg.values
CIN  = cin_msg.values
HLCY = hlcy_msg.values

lats, lons = cape_msg.latlons()

# =========================
# COMPUTE PROBABILITY
# =========================
linear = (
    INTERCEPT
    + COEFFS["CAPE"] * CAPE
    + COEFFS["CIN"]  * CIN
    + COEFFS["HLCY"] * HLCY
)

prob = 1 / (1 + np.exp(-linear))

# =========================
# WRITE JSON (CRITICAL)
# =========================
features = []

rows, cols = prob.shape
for i in range(rows):
    for j in range(cols):
        features.append({
            "lat": float(lats[i, j]),
            "lon": float(lons[i, j]),
            "prob": float(prob[i, j])
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f)

print("✅ Tornado probability JSON written")
print("TOTAL GRID POINTS:", len(features))
print("OUTPUT:", OUTPUT_JSON)
