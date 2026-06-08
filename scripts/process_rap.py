import os
import urllib.request
import numpy as np
import json
import datetime
import requests
import rasterio

DATA_DIR = "data"
RASTER_PATH = "data/nbm.tif"
OUTPUT_JSON = "map/data/tornado_prob_nbm_lcc.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

NBM_URL = "https://noaa-nbm-pds.s3.amazonaws.com/blendv5.0/conus/2026/06/06/1500/spctor4hr/blendv5.0_conus_spctor4hr_2026-06-06T15%3A00_2026-06-06T19%3A00.tif"


def url_exists(url):
    return requests.head(url).status_code == 200


print("Checking NBM file...")

if not url_exists(NBM_URL):
    print("NBM not ready")
    exit(0)

urllib.request.urlretrieve(NBM_URL, RASTER_PATH)
print("Downloaded")

with rasterio.open(RASTER_PATH) as src:
    prob = src.read(1).astype(float)
    transform = src.transform
    crs = src.crs

print("RAW MIN/MAX:", np.nanmin(prob), np.nanmax(prob))

# SIMPLE NORMALIZATION (safe)
if np.nanmax(prob) <= 1.0:
    prob *= 100.0

rows, cols = prob.shape

dx = abs(transform.a)
dy = abs(transform.e)

flat = prob.flatten()

output = {
    "run_date": "2026-06-06",
    "run_hour": "15",
    "forecast": "SPCTOR4HR",
    "generated": datetime.datetime.utcnow().isoformat() + "Z",

    "width": cols,
    "height": rows,

    "dx": dx,
    "dy": dy,

    "transform": [
        transform.c,
        transform.f
    ],

    "crs": str(crs),

    "probabilities": [
        None if np.isnan(v) else round(float(v), 2)
        for v in flat
    ]
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, separators=(",", ":"))

print("Saved OK")
