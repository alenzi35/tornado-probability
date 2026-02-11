import os
import urllib.request
import pygrib
import numpy as np
import json
from pyproj import CRS, Transformer

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

# Output JSON — new filename to avoid confusion with old lat/lon JSON
OUTPUT_JSON = "map/data/tornado_prob_lcc.json"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"

# Logistic regression coefficients
INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# ---------------- SETUP ----------------
os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- DOWNLOAD ----------------
print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete.")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

# ---------------- PICK VARIABLE ----------------
def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        print(f"Found {shortname}")
        return g
    raise RuntimeError(f"{shortname} not found")

# ---------------- LOAD VARIABLES ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")
grbs.seek(0)
cin_msg = pick_var(grbs, "cin", typeOfLevel="surface")
grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", typeOfLevel="heightAboveGroundLayer", bottom=0, top=1000)

# Clean NaNs
cape = np.nan_to_num(cape_msg.values, nan=0.0)
cin  = np.nan_to_num(cin_msg.values, nan=0.0)
hlcy = np.nan_to_num(hlcy_msg.values, nan=0.0)

# ---------------- LAT/LON GRID ----------------
lats, lons = cape_msg.latlons()
rows, cols = lats.shape

# ---------------- PROJECTION TO LCC ----------------
proj_params = cape_msg.projparams
print("Projection parameters from GRIB:")
for k, v in proj_params.items():
    print(f"  {k}: {v}")

crs_lcc = CRS(proj_params)  # native LCC
crs_wgs = CRS.from_epsg(4326)  # lat/lon
transformer = Transformer.from_crs(crs_wgs, crs_lcc, always_xy=True)

# Flatten, transform, then reshape to match grid
flat_lons = lons.flatten()
flat_lats = lats.flatten()
flat_x, flat_y = transformer.transform(flat_lons, flat_lats)
xx = np.array(flat_x).reshape(rows, cols)
yy = np.array(flat_y).reshape(rows, cols)

# ---------------- PROBABILITY ----------------
linear = INTERCEPT + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- WRITE JSON ----------------
features = []
for i in range(rows):
    for j in range(cols):
        features.append({
            "x": float(xx[i,j]),  # LCC X in meters
            "y": float(yy[i,j]),  # LCC Y in meters
            "prob": float(prob[i,j])
        })

output = {
    "projection": proj_params,
    "features": features
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("JSON written:", OUTPUT_JSON)
print("Points:", len(features))
print("File size:", os.path.getsize(OUTPUT_JSON), "bytes")
