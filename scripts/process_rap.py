import os
import urllib.request
import pygrib
import numpy as np
import json
import math

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

RAD2DEG = 180.0 / math.pi
DX_KM = 13.545   # RAP grid spacing
# ----------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete")

grbs = pygrib.open(GRIB_PATH)

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if abs(g.bottomLevel - bottom) > 1:
                continue
        print(f"✅ Found {shortname}")
        return g
    raise RuntimeError(f"{shortname} NOT FOUND")

# ---------------- LOAD VARIABLES ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")

grbs.seek(0)
cin_msg = pick_var(grbs, "cin", typeOfLevel="surface")

grbs.seek(0)
hlcy_msg = pick_var(
    grbs,
    "hlcy",
    typeOfLevel="heightAboveGroundLayer",
    bottom=0,
    top=1000
)

cape = cape_msg.values
cin = cin_msg.values
hlcy = hlcy_msg.values

lats_rad, lons_rad = cape_msg.latlons()

# ---------------- CONVERT TO DEGREES ----------------
lats = lats_rad * RAD2DEG
lons = lons_rad * RAD2DEG

# ---------------- COMPUTE PROBABILITY ----------------
linear = (
    INTERCEPT
    + COEFFS["CAPE"] * cape
    + COEFFS["CIN"] * cin
    + COEFFS["HLCY"] * hlcy
)
prob = 1 / (1 + np.exp(-linear))

# ---------------- BUILD CELL EXTENTS ----------------
rows, cols = prob.shape

dlat = abs(lats[1, 0] - lats[0, 0])
dlon = abs(lons[0, 1] - lons[0, 0])

features = []

for i in range(rows):
    for j in range(cols):
        lat_c = lats[i, j]
        lon_c = lons[i, j]

        features.append({
            "lat_min": float(lat_c - dlat / 2),
            "lat_max": float(lat_c + dlat / 2),
            "lon_min": float(lon_c - dlon / 2),
            "lon_max": float(lon_c + dlon / 2),
            "prob": float(prob[i, j])
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f)

print("✅ JSON written:", OUTPUT_JSON)
print("TOTAL CELLS:", len(features))
