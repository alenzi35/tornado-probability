import os
import urllib.request
import pygrib
import numpy as np
import json


# ---------------- CONFIG ----------------

DATE = "20260128"
HOUR = "19"
FCST = "02"

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


# ---------------- SETUP ----------------

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)


# ---------------- DOWNLOAD ----------------

print("Downloading RAP...")

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

            if not (abs(g.bottomLevel - bottom) < 1 and
                    abs(g.topLevel - top) < 1):
                continue

        print(f"Found {shortname}")

        return g

    raise RuntimeError(f"{shortname} not found")


# ---------------- LOAD DATA ----------------

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

lats, lons = cape_msg.latlons()


# ---------------- GRID SPACING ----------------

lat_step = float(np.mean(np.diff(lats[:, 0])))
lon_step = float(np.mean(np.diff(lons[0, :])))

print(f"Grid spacing: {lat_step:.4f}°, {lon_step:.4f}°")


# ---------------- CLEAN NaNs ----------------

cape = np.nan_to_num(cape, nan=0.0)
cin  = np.nan_to_num(cin, nan=0.0)
hlcy = np.nan_to_num(hlcy, nan=0.0)


# ---------------- PROBABILITY ----------------

linear = (
    INTERCEPT +
    COEFFS["CAPE"] * cape +
    COEFFS["CIN"]  * cin +
    COEFFS["HLCY"] * hlcy
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
            "latStep": lat_step,
            "lonStep": lon_step
        })


with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f)


print("JSON written:", OUTPUT_JSON)
print("Points:", len(features))
print("File size:", os.path.getsize(OUTPUT_JSON), "bytes")
