import os
import urllib.request
import pygrib
import numpy as np
import json
import datetime
import requests
import zipfile
import io

import geopandas as gpd
from shapely.geometry import box
from shapely.prepared import prep
from pyproj import Proj

# ================= CONFIG =================

DATA_DIR = "data"
GRIB_PATH = "data/nbm.grib2"
OUTPUT_JSON = "map/data/tornado_prob_nbm_lcc.json"

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= TIME =================

def get_target_cycle():
    now = datetime.datetime.utcnow()
    run_time = now - datetime.timedelta(hours=1)

    date = run_time.strftime("%Y%m%d")
    hour = run_time.strftime("%H")

    return date, hour

DATE, HOUR = get_target_cycle()

FCST = "006"  # NBM commonly uses 3h steps (f003, f006, etc.)

print("Target:", DATE, HOUR, "F" + FCST)

# ================= DOWNLOAD NBM =================

NBM_URL = f"https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.{DATE}/{HOUR}/grib2/blend.t{HOUR}z.core.f{FCST}.co.grib2"

print("URL:", NBM_URL)

def url_exists(url):
    r = requests.head(url)
    return r.status_code == 200

if not url_exists(NBM_URL):
    print("NBM file not ready yet. Skipping.")
    exit(0)

urllib.request.urlretrieve(NBM_URL, GRIB_PATH)
print("Downloaded NBM GRIB2")

# ================= LOAD GRIB =================

grbs = pygrib.open(GRIB_PATH)

def pick_torprob(grbs):

    for g in grbs:
        name = getattr(g, "shortName", "").lower()
        if name == "torprob":
            return g

        # fallback (NBM inconsistency)
        if "tor" in name and "prob" in name:
            return g

    raise RuntimeError("TORPROB not found")

grbs.seek(0)
tor_msg = pick_torprob(grbs)

# ================= ARRAY =================

prob = np.nan_to_num(tor_msg.values)

# convert to percent if needed
if np.nanmax(prob) <= 1.0:
    prob = prob * 100.0

print("Mean probability (%):", np.mean(prob))

# ================= GRID =================

lats, lons = tor_msg.latlons()
params = tor_msg.projparams

proj_lcc = Proj(
    proj="lcc",
    lat_1=params["lat_1"],
    lat_2=params["lat_2"],
    lat_0=params["lat_0"],
    lon_0=params["lon_0"],
    a=params.get("a", 6371229),
    b=params.get("b", 6371229)
)

x_vals, y_vals = proj_lcc(lons, lats)

# ================= CONUS MASK =================

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

lower48_lcc = lower48.to_crs(proj_lcc.srs)
conus_poly = lower48_lcc.unary_union
prepared_conus = prep(conus_poly)

# ================= FILTER GRID =================

print("Filtering grid cells...")

features = []

rows, cols = prob.shape

for i in range(rows):
    for j in range(cols):

        x = x_vals[i, j]
        y = y_vals[i, j]

        dx = x_vals[i, j+1] - x if j < cols-1 else x - x_vals[i, j-1]
        dy = y_vals[i+1, j] - y if i < rows-1 else y - y_vals[i-1, j]

        dx, dy = abs(dx), abs(dy)

        cell_box = box(x, y, x + dx, y + dy)

        if prepared_conus.intersects(cell_box):

            features.append({
                "x": float(x),
                "y": float(y),
                "dx": float(dx),
                "dy": float(dy),
                "prob": float(prob[i, j])
            })

print(f"Kept {len(features)} CONUS cells")

# ================= OUTPUT =================

output = {
    "run_date": DATE,
    "run_hour": HOUR,
    "forecast": "F" + FCST,
    "generated": datetime.datetime.utcnow().isoformat() + "Z",
    "projection": params,
    "features": features
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("Saved:", OUTPUT_JSON)
print("DONE.")
