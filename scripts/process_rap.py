import os
import urllib.request
import numpy as np
import json
import datetime
import requests
import zipfile
import io
import rasterio

import geopandas as gpd
from shapely.geometry import box
from shapely.prepared import prep

# ================= CONFIG =================

DATA_DIR = "data"
RASTER_PATH = "data/nbm.tif"
OUTPUT_JSON = "map/data/tornado_prob_nbm_lcc.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= FILE SOURCE =================

NBM_URL = "https://noaa-nbm-pds.s3.amazonaws.com/blendv5.0/conus/2026/06/06/1500/spctor4hr/blendv5.0_conus_spctor4hr_2026-06-06T15%3A00_2026-06-06T19%3A00.tif"

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

# ================= DOWNLOAD =================

def url_exists(url):
    r = requests.head(url)
    return r.status_code == 200

print("Checking NBM file...")

if not url_exists(NBM_URL):
    print("NBM file not ready yet.")
    exit(0)

urllib.request.urlretrieve(NBM_URL, RASTER_PATH)
print("Downloaded NBM GeoTIFF")

# ================= LOAD RASTER =================

with rasterio.open(RASTER_PATH) as src:
    prob = src.read(1).astype(float)
    transform = src.transform
    crs = src.crs

rows, cols = prob.shape

print("Raster shape:", rows, cols)
print("Mean probability:", np.nanmean(prob))

# normalize if needed
if np.nanmax(prob) <= 1.0:
    prob = prob * 100.0

# ================= CONUS MASK =================

def download_shapefile(url, folder):
    resp = requests.get(url)
    resp.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    z.extractall(folder)

    shp_file = [f for f in z.namelist() if f.endswith(".shp")][0]

    return gpd.read_file(f"{folder}/{shp_file}")

print("Downloading CONUS shapefile...")

states = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")

lower48 = states[~states["STUSPS"].isin(["AK", "HI", "PR"])]

lower48 = lower48.to_crs(crs)

conus_poly = lower48.unary_union
prepared_conus = prep(conus_poly)

# ================= MASK RASTER =================

print("Applying CONUS mask...")

flat_probs = []
x_coords = []
y_coords = []

dx = abs(transform.a)
dy = abs(transform.e)

for i in range(rows):
    for j in range(cols):

        val = prob[i, j]

        if np.isnan(val):
            flat_probs.append(None)
            continue

        x, y = rasterio.transform.xy(transform, i, j)

        cell = box(x, y, x + dx, y + dy)

        if prepared_conus.intersects(cell):
            flat_probs.append(round(float(val), 2))
        else:
            flat_probs.append(None)

# ================= OUTPUT =================

output = {
    "run_date": "2026-06-06",
    "run_hour": "15",
    "forecast": "SPCTOR4HR",
    "generated": datetime.datetime.utcnow().isoformat() + "Z",

    "width": cols,
    "height": rows,

    "transform": [
        transform.a,
        transform.b,
        transform.c,
        transform.d,
        transform.e,
        transform.f
    ],

    "crs": str(crs),

    "probabilities": flat_probs
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, separators=(",", ":"))

print("Saved:", OUTPUT_JSON)
print("DONE.")
