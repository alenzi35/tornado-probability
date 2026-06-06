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
from pyproj import CRS

# ================= CONFIG =================

DATA_DIR = "data"
GRIB_PATH = "data/nbm.tif"
OUTPUT_JSON = "map/data/tornado_prob_nbm_lcc.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= FILE SOURCE =================

NBM_URL = "https://noaa-nbm-pds.s3.amazonaws.com/blendv5.0/conus/2026/06/06/1500/spctor4hr/blendv5.0_conus_spctor4hr_2026-06-06T15%3A00_2026-06-06T19%3A00.tif"

# US Census lower 48 states shapefile
CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

# ================= DOWNLOAD NBM =================

def url_exists(url):
    r = requests.head(url)
    return r.status_code == 200

print("Checking NBM file...")

if not url_exists(NBM_URL):
    print("NBM file not ready yet. Skipping.")
    exit(0)

urllib.request.urlretrieve(NBM_URL, GRIB_PATH)
print("Downloaded NBM GeoTIFF")

# ================= LOAD RASTER =================

with rasterio.open(GRIB_PATH) as src:
    prob = src.read(1).astype(float)
    transform = src.transform
    crs = src.crs

print("Raw mean probability:", np.nanmean(prob))

# normalize if needed
if np.nanmax(prob) <= 1.0:
    prob = prob * 100.0

print("Current mean probability (%):", np.nanmean(prob))

# ================= DOWNLOAD CONUS SHAPE =================

def download_shapefile(url, folder):
    resp = requests.get(url)
    resp.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    z.extractall(folder)

    shp_file = [f for f in z.namelist() if f.endswith(".shp")][0]

    return gpd.read_file(f"{folder}/{shp_file}")

print("Downloading CONUS shapefile...")

states_gdf = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")

lower48 = states_gdf[~states_gdf["STUSPS"].isin(["AK", "HI", "PR"])]

# reproject to raster CRS
lower48 = lower48.to_crs(crs)

conus_poly = lower48.unary_union
prepared_conus = prep(conus_poly)

# ================= FILTER CELLS =================

print("Filtering grid cells to CONUS...")

features = []

rows, cols = prob.shape

for i in range(rows):
    for j in range(cols):

        val = prob[i, j]

        if np.isnan(val):
            continue

        # convert raster index → spatial coords
        x, y = rasterio.transform.xy(transform, i, j)

        # approximate cell size
        if j < cols - 1:
            x2, _ = rasterio.transform.xy(transform, i, j + 1)
            dx = abs(x2 - x)
        else:
            dx = 0

        if i < rows - 1:
            _, y2 = rasterio.transform.xy(transform, i + 1, j)
            dy = abs(y2 - y)
        else:
            dy = 0

        cell_box = box(x, y, x + dx, y + dy)

        if prepared_conus.intersects(cell_box):

            features.append({
                "x": float(x),
                "y": float(y),
                "dx": float(dx),
                "dy": float(dy),
                "prob": float(val)
            })

print(f"Kept {len(features)} CONUS cells")

# ================= OUTPUT =================

valid_start = "15:00"
valid_end = "19:00"

output = {
    "run_date": "2026-06-06",
    "run_hour": "15",
    "forecast": "SPCTOR4HR",
    "valid": f"{valid_start}-{valid_end} UTC",
    "generated": datetime.datetime.utcnow().isoformat() + "Z",
    "projection": {
        "crs": str(crs)
    },
    "features": features
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("Saved:", OUTPUT_JSON)
print("DONE.")
