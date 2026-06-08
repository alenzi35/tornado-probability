import os
import urllib.request
import numpy as np
import json
import datetime
import requests
import rasterio

# ================= CONFIG =================

DATA_DIR = "data"
RASTER_PATH = "data/nbm.tif"
OUTPUT_JSON = "map/data/tornado_prob_nbm_lcc.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

NBM_URL = "https://noaa-nbm-pds.s3.amazonaws.com/blendv5.0/conus/2026/06/06/1500/spctor4hr/blendv5.0_conus_spctor4hr_2026-06-06T15%3A00_2026-06-06T19%3A00.tif"


# ================= DOWNLOAD =================

def url_exists(url):
    return requests.head(url).status_code == 200

print("Checking NBM file...")

if not url_exists(NBM_URL):
    print("NBM not ready")
    exit(0)

urllib.request.urlretrieve(NBM_URL, RASTER_PATH)
print("Downloaded NBM")


# ================= LOAD + AUTO BAND DETECTION =================

with rasterio.open(RASTER_PATH) as src:

    print("Raster bands:", src.count)

    best_band = None
    best_range = 0

    # pick band with highest variability (this fixes your issue)
    for i in range(1, src.count + 1):
        arr = src.read(i).astype(float)

        arr_clean = arr[~np.isnan(arr)]
        if len(arr_clean) == 0:
            continue

        r = np.nanmax(arr_clean) - np.nanmin(arr_clean)

        print(f"Band {i} min/max:", np.nanmin(arr_clean), np.nanmax(arr_clean))

        if r > best_range:
            best_range = r
            best_band = i

    print("Selected band:", best_band)

    prob = src.read(best_band).astype(float)
    transform = src.transform
    crs = src.crs


# ================= CLEAN DATA =================

prob = np.nan_to_num(prob)

mx = np.nanmax(prob)

print("FINAL RAW RANGE:", np.nanmin(prob), mx)

# normalize safely
if mx <= 1.5:
    prob *= 100.0

rows, cols = prob.shape

dx = abs(transform.a)
dy = abs(transform.e)

origin_x = transform.c
origin_y = transform.f

flat = prob.flatten()


# ================= OUTPUT =================

output = {
    "run_date": "2026-06-06",
    "run_hour": "15",
    "forecast": "SPCTOR4HR",
    "generated": datetime.datetime.utcnow().isoformat() + "Z",

    "width": cols,
    "height": rows,

    "dx": dx,
    "dy": dy,

    "transform": [origin_x, origin_y],

    "crs": str(crs),

    "probabilities": [
        None if np.isnan(v) else round(float(v), 2)
        for v in flat
    ]
}


# ================= SAVE =================

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, separators=(",", ":"))

print("Saved:", OUTPUT_JSON)
print("DONE")
