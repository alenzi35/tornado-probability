import os
import urllib.request
import pygrib
import numpy as np
from PIL import Image
import json
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from pyproj import Transformer
from math import ceil
import subprocess

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"

OUTPUT_DIR = "map/tiles"
OUTPUT_JSON = "map/data/tornado_prob_pixels.json"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# ----------------------------------------

os.makedirs("data", exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- Download RAP ----------------
print("Downloading RAP...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete")

# ---------------- Open GRIB ----------------
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
            if abs(g.bottomLevel-bottom)>1 or abs(g.topLevel-top)>1:
                continue
        return g
    raise RuntimeError(f"{shortname} NOT FOUND")

# ---------------- Extract fields ----------------
grbs.seek(0)
cape_msg = pick_var(grbs,"cape","surface")
cape = cape_msg.values

grbs.seek(0)
cin = pick_var(grbs,"cin","surface").values

grbs.seek(0)
hlcy = pick_var(grbs,"hlcy","heightAboveGroundLayer",0,1000).values

lats, lons = cape_msg.latlons()
rows, cols = cape.shape

# ---------------- Probability ----------------
linear = INTERCEPT + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
prob = 1/(1+np.exp(-linear))

# ---------------- Build raster ----------------
print("Creating probability raster...")
# Create a 3D RGB array for visualization
rgb = np.zeros((rows, cols, 3), dtype=np.uint8)

for i in range(rows):
    for j in range(cols):
        p = np.clip(prob[i,j],0,1)
        if p < 0.3:
            r = int(255*(p/0.3))
            g_val = int(255*(p/0.3))
            b = 255
        elif p < 0.6:
            r = 255
            g_val = int(255*(1-(p-0.3)/0.3))
            b = 0
        else:
            r = 255
            g_val = int(255*(1-(p-0.6)/0.4))
            b = 0
        rgb[i,j] = [r, g_val, b]

# ---------------- Reproject to Web Mercator ----------------
print("Reprojecting to Web Mercator...")

# Transform from LCC (native RAP) → EPSG:3857
transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
lon_min, lon_max = np.min(lons), np.max(lons)
lat_min, lat_max = np.min(lats), np.max(lats)
x_min, y_min = transformer.transform(lon_min, lat_min)
x_max, y_max = transformer.transform(lon_max, lat_max)

# Create rasterio dataset
raster_path = "map/data/tornado_prob_merc.tif"
transform = from_bounds(x_min, y_min, x_max, y_max, cols, rows)

with rasterio.open(
    raster_path,
    'w',
    driver='GTiff',
    height=rows,
    width=cols,
    count=3,
    dtype=rgb.dtype,
    crs=CRS.from_epsg(3857),
    transform=transform
) as dst:
    for i in range(3):
        dst.write(rgb[:,:,i], i+1)

# ---------------- Generate tiles ----------------
print("Generating map tiles (Leaflet-ready)...")

# Requires gdal2tiles.py installed (comes with GDAL)
tiles_dir = OUTPUT_DIR
subprocess.run([
    "gdal2tiles.py",
    "-z", "1-9",
    "-w", "leaflet",
    raster_path,
    tiles_dir
])

# ---------------- JSON output ----------------
print("Writing JSON for interactivity...")
features = []
for i in range(rows):
    for j in range(cols):
        features.append({
            "row":i,
            "col":j,
            "prob":float(prob[i,j])
        })

with open(OUTPUT_JSON,"w") as f:
    json.dump(features,f)

print("DONE! Leaflet tiles in", tiles_dir)
