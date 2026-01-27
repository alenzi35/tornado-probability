import os
import urllib.request
import pygrib
import numpy as np
import json

# ---------------- CONFIG ----------------
DATE = "20260126"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awp130pgrbf{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

# Logistic regression coefficients for 1-hour probability
INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}
# ----------------------------------------

# ---------------- CREATE FOLDERS ----------------
os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- DOWNLOAD RAP ----------------
print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete.")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

def pick_var(grbs, shortname):
    """Pick first GRIB message with given shortName"""
    for g in grbs:
        if g.shortName.lower() == shortname.lower():
            print(f"✅ Found {shortname}: level {g.level} ({g.typeOfLevel})")
            return g
    raise RuntimeError(f"{shortname} NOT FOUND")

# ---------------- EXTRACT VARIABLES ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape")
grbs.seek(0)
cin_msg  = pick_var(grbs, "cin")
grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy")

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

lats, lons = cape_msg.latlons()

# ---------------- COMPUTE PROBABILITY ----------------
linear = INTERCEPT + COEFFS["CAPE"] * cape + COEFFS["CIN"] * cin + COEFFS["HLCY"] * hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- WRITE JSON ----------------
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
    json.dump(features, f, indent=2)

print("✅ Tornado probability JSON written to:", OUTPUT_JSON)
print("TOTAL GRID POINTS:", len(features))
print("FILE SIZE:", os.path.getsize(OUTPUT_JSON), "bytes")
