import pygrib
import numpy as np
import json
import os
import urllib.request

# ---------------- CONFIG ----------------
DATE = "20260126"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awp130pgrbf{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}
# ----------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete.")

grbs = pygrib.open(GRIB_PATH)

def pick(grbs, short):
    for g in grbs:
        if g.shortName.lower() == short.lower():
            print(f"✅ Found {short}: level {g.level} ({g.typeOfLevel})")
            return g
    raise RuntimeError(f"{short} NOT FOUND")

cape_msg = pick(grbs, "cape")
cin_msg  = pick(grbs, "cin")
hlcy_msg = pick(grbs, "hlcy")

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

lats, lons = cape_msg.latlons()

# --- probability ---
linear = (
    INTERCEPT
    + cape * COEFFS["CAPE"]
    + cin  * COEFFS["CIN"]
    + hlcy * COEFFS["HLCY"]
)

prob = 1 / (1 + np.exp(-linear))

# --- WRITE JSON ---
features = []

ny, nx = prob.shape
for i in range(ny):
    for j in range(nx):
        features.append({
            "lat": float(lats[i, j]),
            "lon": float(lons[i, j]),
            "prob": float(prob[i, j])
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f)

print("WROTE FILE:", OUTPUT_JSON)
print("TOTAL GRID POINTS:", len(features))
print("FILE SIZE:", os.path.getsize(OUTPUT_JSON), "bytes")
