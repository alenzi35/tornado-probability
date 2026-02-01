import os
import urllib.request
import pygrib
import numpy as np
import json
from pyproj import Proj, transform

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

# RAP GRIB file URL (AWIP32 product)
RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

# Logistic regression coefficients
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
print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete.")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

# ---------------- HELPER ----------------
def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel") or not hasattr(g, "topLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        print(f"✅ Found {shortname}: level {g.typeOfLevel}")
        return g
    raise RuntimeError(f"{shortname} NOT FOUND with specified level criteria")

# ---------------- EXTRACT VARIABLES ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")
grbs.seek(0)
cin_msg  = pick_var(grbs, "cin", typeOfLevel="surface")
grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", typeOfLevel="heightAboveGroundLayer", bottom=0, top=1000)

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

lats, lons = cape_msg.latlons()

# ---------------- LCC PROJECTION ----------------
# Lambert Conformal Conic (match RAP)
proj_lcc = Proj(proj='lcc', lat_1=25, lat_2=60, lat_0=38, lon_0=-97, x_0=0, y_0=0, units='m')

# ---------------- COMPUTE PROBABILITY ----------------
linear = INTERCEPT + COEFFS["CAPE"] * cape + COEFFS["CIN"] * cin + COEFFS["HLCY"] * hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- WRITE JSON ----------------
features = []
rows, cols = prob.shape
for i in range(rows):
    for j in range(cols):
        lat = float(lats[i,j])
        lon = float(lons[i,j])
        px, py = proj_lcc(lon, lat)  # convert to LCC meters
        features.append({
            "lat": lat,
            "lon": lon,
            "x": px,
            "y": py,
            "prob": float(prob[i,j])
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f, indent=2)

print("✅ Tornado probability JSON written to:", OUTPUT_JSON)
print("TOTAL GRID POINTS:", len(features))
print("FILE SIZE:", os.path.getsize(OUTPUT_JSON), "bytes")
