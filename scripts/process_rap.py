import os
import urllib.request
import pygrib
import numpy as np
import json


# ================= CONFIG =================

DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob_lcc.json"


# Logistic regression coefficients
INTERCEPT = -1.5686

COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}


# ================= SETUP =================

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)


# ================= DOWNLOAD =================

print("Downloading RAP...")

urllib.request.urlretrieve(RAP_URL, GRIB_PATH)

print("Download complete.")


# ================= OPEN GRIB =================

grbs = pygrib.open(GRIB_PATH)


# ================= PICK VARIABLE =================

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):

    for g in grbs:

        if g.shortName.lower() != shortname.lower():
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if bottom is not None and top is not None:

            if not hasattr(g, "bottomLevel"):
                continue

            if not (abs(g.bottomLevel - bottom) < 1 and
                    abs(g.topLevel - top) < 1):
                continue

        print(f"Found {shortname}")

        return g

    raise RuntimeError(f"{shortname} not found")


# ================= LOAD DATA =================

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
cin  = cin_msg.values
hlcy = hlcy_msg.values


# ================= GET LCC X/Y =================

# Native projection coordinates (meters)
x_vals, y_vals = cape_msg.projcoords()

print("Loaded LCC coordinates")


# ================= CLEAN NaNs =================

cape = np.nan_to_num(cape, nan=0.0)
cin  = np.nan_to_num(cin, nan=0.0)
hlcy = np.nan_to_num(hlcy, nan=0.0)


# ================= PROBABILITY =================

linear = (
    INTERCEPT +
    COEFFS["CAPE"] * cape +
    COEFFS["CIN"]  * cin +
    COEFFS["HLCY"] * hlcy
)

prob = 1 / (1 + np.exp(-linear))


# ================= BUILD FEATURES =================

features = []

rows, cols = prob.shape

print("Grid size:", rows, "x", cols)


for i in range(rows):
    for j in range(cols):

        x = x_vals[i, j]
        y = y_vals[i, j]

        # --- Compute true cell size from neighbors ---

        # dx
        if j < cols - 1:
            dx = x_vals[i, j+1] - x_vals[i, j]
        else:
            dx = x_vals[i, j] - x_vals[i, j-1]

        # dy
        if i < rows - 1:
            dy = y_vals[i+1, j] - y_vals[i, j]
        else:
            dy = y_vals[i, j] - y_vals[i-1, j]

        features.append({
            "x": float(x),
            "y": float(y),
            "dx": float(abs(dx)),
            "dy": float(abs(dy)),
            "prob": float(prob[i, j])
        })


# ================= WRITE JSON =================

output = {
    "projection": {
        "proj": "lcc",
        "lon_0": float(cape_msg.projparams.get("lon_0", 0)),
        "lat_0": float(cape_msg.projparams.get("lat_0", 0)),
        "lat_1": float(cape_msg.projparams.get("lat_1", 0)),
        "lat_2": float(cape_msg.projparams.get("lat_2", 0)),
        "a": float(cape_msg.projparams.get("a", 0)),
        "b": float(cape_msg.projparams.get("b", 0))
    },
    "features": features
}


with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)


print("JSON written:", OUTPUT_JSON)
print("Points:", len(features))
print("File size:", os.path.getsize(OUTPUT_JSON), "bytes")
