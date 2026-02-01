import os
import urllib.request
import pygrib
import numpy as np
import json

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"
RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

INTERCEPT = -1.5686
COEFFS = {"CAPE": 2.88592370e-03, "CIN": 2.38728498e-05, "HLCY": 8.85192696e-03}

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)

grbs = pygrib.open(GRIB_PATH)
def get_v(name, **kwargs):
    grbs.seek(0)
    return grbs.select(shortName=name, **kwargs)[0]

cape = get_v("cape", typeOfLevel="surface").values
cin = get_v("cin", typeOfLevel="surface").values
hlcy_m = get_v("hlcy", typeOfLevel="heightAboveGroundLayer", bottomLevel=0, topLevel=1000)
hlcy = hlcy_m.values
lats, lons = hlcy_m.latlons()

# Calculate actual grid resolution for tiling
d_lat = float(np.abs(lats[1,0] - lats[0,0]))
d_lon = float(np.abs(lons[0,1] - lons[0,0]))

linear = INTERCEPT + (COEFFS["CAPE"] * cape) + (COEFFS["CIN"] * cin) + (COEFFS["HLCY"] * hlcy)
prob = 1 / (1 + np.exp(-linear))

features = []
rows, cols = prob.shape
for i in range(rows):
    for j in range(cols):
        features.append({
            "lt": float(lats[i, j]),
            "ln": float(lons[i, j]),
            "p": float(prob[i, j])
        })

with open(OUTPUT_JSON, "w") as f:
    json.dump({"meta": {"d_lat": d_lat, "d_lon": d_lon}, "cells": features}, f)

print(f"✅ Processed {len(features)} cells.")
