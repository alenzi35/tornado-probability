import os
import urllib.request
import pygrib
import numpy as np
import json

# ==========================================================
# TARGET CASE
# Init: 2026-01-28 19:00 UTC
# Forecast: +2h
# ==========================================================

DATE_STR = "20260128"
HOUR_STR = "19"
FCST = "02"

RAP_URL = (
    f"https://noaa-rap-pds.s3.amazonaws.com/"
    f"rap.{DATE_STR}/rap.t{HOUR_STR}z.awip32f{FCST}.grib2"
)

GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# ---------------- CREATE FOLDERS ----------------
os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- DOWNLOAD RAP ----------------
print("Downloading:", RAP_URL)
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

def pick_var(grbs, shortname, typeOfLevel, bottom, top):
    for g in grbs:
        if (
            g.shortName.lower() == shortname
            and g.typeOfLevel == typeOfLevel
            and getattr(g, "bottomLevel", None) == bottom
            and getattr(g, "topLevel", None) == top
        ):
            print(f"✅ Found {shortname}: {typeOfLevel} {bottom}-{top}")
            return g
    raise RuntimeError(f"{shortname} {typeOfLevel} {bottom}-{top} NOT FOUND")

# ---------------- EXTRACT VARIABLES ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", "pressureLayer", 0, 90)

grbs.seek(0)
cin_msg  = pick_var(grbs, "cin", "pressureLayer", 0, 90)

grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

lats, lons = cape_msg.latlons()

lat_size = float(np.mean(np.diff(lats[:, 0])))
lon_size = float(np.mean(np.diff(lons[0, :])))

# ---------------- COMPUTE PROBABILITY ----------------
linear = (
    INTERCEPT
    + COEFFS["CAPE"] * cape
    + COEFFS["CIN"] * cin
    + COEFFS["HLCY"] * hlcy
)

prob = 1 / (1 + np.exp(-linear))

# ---------------- WRITE JSON ----------------
features = []
rows, cols = prob.shape

for i in range(rows):
    for j in range(cols):
        features.append({
            "lat": float(lats[i, j]),
            "lon": float(lons[i, j]),
            "prob": float(prob[i, j]),
            "lat_size": lat_size,
            "lon_size": lon_size
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f)

print("✅ tornado_prob.json written")
print("Grid points:", len(features))
print("Cell size:", lat_size, lon_size)
