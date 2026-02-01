import os
import urllib.request
import pygrib
import numpy as np
from pyproj import Proj
from PIL import Image

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_IMG = "map/data/tornado_prob.png"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

print("Downloading RAP...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)

grbs = pygrib.open(GRIB_PATH)

def pick(grbs, name):
    for g in grbs:
        if g.shortName == name:
            return g
    raise RuntimeError(f"{name} not found")

grbs.seek(0)
cape = pick(grbs, "cape").values
grbs.seek(0)
cin  = pick(grbs, "cin").values
grbs.seek(0)
hlcy = pick(grbs, "hlcy").values

linear = INTERCEPT + (
    COEFFS["CAPE"] * cape +
    COEFFS["CIN"]  * cin +
    COEFFS["HLCY"] * hlcy
)

prob = 1 / (1 + np.exp(-linear))

# Normalize 0–255
img = (np.clip(prob, 0, 1) * 255).astype(np.uint8)

Image.fromarray(img).save(OUTPUT_IMG)

print("✅ Image written:", OUTPUT_IMG)
