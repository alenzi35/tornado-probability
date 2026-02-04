import os
import urllib.request
import pygrib
import numpy as np
from PIL import Image
import json
from pyproj import Proj

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob_lcc.json"
OUTPUT_PNG  = "map/data/tornado_prob_lcc.png"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}
# ----------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- Download RAP ----------------
print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete.")

# ---------------- Open GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

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
    raise RuntimeError(f"{shortname} NOT FOUND")

# ---------------- Extract variables ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")
grbs.seek(0)
cin_msg  = pick_var(grbs, "cin", typeOfLevel="surface")
grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", typeOfLevel="heightAboveGroundLayer", bottom=0, top=1000)

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

lats, lons = cape_msg.latlons()  # in degrees
rows, cols = cape.shape

# ---------------- Compute probability ----------------
linear = INTERCEPT + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
prob = 1/(1+np.exp(-linear))

# ---------------- LCC projection (native RAP grid) ----------------
lcc = Proj(proj='lcc', lat_1=33, lat_2=45, lat_0=40, lon_0=-97, x_0=0, y_0=0, ellps='GRS80')
x, y = lcc(lons, lats)  # meters

# Normalize coordinates for image
x_min, x_max = x.min(), x.max()
y_min, y_max = y.min(), y.max()
width, height = cols, rows  # one pixel per RAP cell

# Create raster image (RGB, probability as red channel)
img = Image.new('RGB', (width, height))
for i in range(rows):
    for j in range(cols):
        p = prob[i,j]
        # Map probability to color
        if p>0.8: color=(128,0,0)
        elif p>0.6: color=(189,0,38)
        elif p>0.4: color=(227,26,28)
        elif p>0.2: color=(252,78,42)
        else: color=(255,237,160)
        img.putpixel((j,i), color)
img.save(OUTPUT_PNG)
print("✅ PNG raster saved:", OUTPUT_PNG)

# ---------------- JSON overlay (optional interactivity) ----------------
features = []
for i in range(rows):
    for j in range(cols):
        features.append({
            "x": float(x[i,j]),
            "y": float(y[i,j]),
            "prob": float(prob[i,j])
        })
with open(OUTPUT_JSON, "w") as f:
    json.dump(features, f, indent=2)
print("✅ JSON overlay saved:", OUTPUT_JSON)
