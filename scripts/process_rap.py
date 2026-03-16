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
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob_lcc.json"

INTERCEPT = -6.274846902965728

COEFFS = {
    "CAPE": 0.0007852504286701655,
    "CIN": -0.003028035273017941,
    "HLCY": 0.008318690761993085
}

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= TIME LOGIC =================

def get_target_cycle():

    now = datetime.datetime.utcnow()

    # RAP files typically appear ~50 minutes after the hour
    run_time = now - datetime.timedelta(hours=1)

    date = run_time.strftime("%Y%m%d")
    hour = run_time.strftime("%H")

    return date, hour


DATE, HOUR = get_target_cycle()
FCST = "01"

# ================= DOWNLOAD RAP =================

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

print("Using RAP run:", DATE, HOUR+"z", "F01")
print("URL:", RAP_URL)


def url_exists(url):
    try:
        r = requests.head(url, timeout=10)
        return r.status_code == 200
    except:
        return False


if not url_exists(RAP_URL):
    print("RAP file not ready yet. Skipping.")
    exit(0)


urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Downloaded RAP GRIB2")

# ================= LOAD GRIB =================

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

            if abs(g.bottomLevel-bottom) > 1:
                continue

            if abs(g.topLevel-top) > 1:
                continue

        return g

    raise RuntimeError(f"{shortname} not found")


# ================= VARIABLES =================

grbs.seek(0)
cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer")

grbs.seek(0)
cin_msg = pick_var(grbs, "cin", "pressureFromGroundLayer")

grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

# Optional extracted fields (for future model improvements)

grbs.seek(0)
t2_msg = pick_var(grbs, "2t", "heightAboveGround")

grbs.seek(0)
d2_msg = pick_var(grbs, "2d", "heightAboveGround")

grbs.seek(0)
u10_msg = pick_var(grbs, "10u", "heightAboveGround")

grbs.seek(0)
v10_msg = pick_var(grbs, "10v", "heightAboveGround")

grbs.seek(0)
u500_msg = pick_var(grbs, "u", "isobaricInhPa")

grbs.seek(0)
v500_msg = pick_var(grbs, "v", "isobaricInhPa")

# ================= ARRAYS =================

cape = np.nan_to_num(cape_msg.values)
cin = np.nan_to_num(cin_msg.values)
hlcy = np.nan_to_num(hlcy_msg.values)

# extracted but unused for now
t2 = np.nan_to_num(t2_msg.values)
td2 = np.nan_to_num(d2_msg.values)
u10 = np.nan_to_num(u10_msg.values)
v10 = np.nan_to_num(v10_msg.values)
u500 = np.nan_to_num(u500_msg.values)
v500 = np.nan_to_num(v500_msg.values)

# ================= GRID =================

lats, lons = cape_msg.latlons()
params = cape_msg.projparams

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

# ================= MODEL =================

linear = (
    INTERCEPT
    + COEFFS["CAPE"] * cape
    + COEFFS["CIN"] * cin
    + COEFFS["HLCY"] * hlcy
)

prob = 1 / (1 + np.exp(-linear))

# ================= LOAD CONUS =================

def download_shapefile(url, folder):

    resp = requests.get(url)
    resp.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    z.extractall(folder)

    shp = [f for f in z.namelist() if f.endswith(".shp")][0]

    return gpd.read_file(f"{folder}/{shp}")


print("Downloading CONUS shapefile...")

states_gdf = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")

lower48 = states_gdf[~states_gdf["STUSPS"].isin(["AK", "HI", "PR"])]

lower48_lcc = lower48.to_crs(proj_lcc.srs)

conus_poly = lower48_lcc.unary_union

prepared_conus = prep(conus_poly)

# ================= FILTER GRID =================

print("Filtering grid cells to CONUS...")

features = []

rows, cols = prob.shape

for i in range(rows):
    for j in range(cols):

        x = x_vals[i, j]
        y = y_vals[i, j]

        if j < cols-1:
            dx = abs(x_vals[i, j+1] - x)
        else:
            dx = abs(x - x_vals[i, j-1])

        if i < rows-1:
            dy = abs(y_vals[i+1, j] - y)
        else:
            dy = abs(y - y_vals[i-1, j])

        cell_box = box(x, y, x+dx, y+dy)

        if prepared_conus.intersects(cell_box):

            features.append({
                "x": float(x),
                "y": float(y),
                "dx": float(dx),
                "dy": float(dy),
                "prob": float(prob[i, j])
            })


print("Cells kept:", len(features))

# ================= OUTPUT =================

valid_start = f"{int(HOUR):02d}:00"
valid_end = f"{(int(HOUR)+1)%24:02d}:00"

output = {
    "run_date": DATE,
    "run_hour": HOUR,
    "forecast": "F01",
    "valid": f"{valid_start}-{valid_end} UTC",
    "generated": datetime.datetime.utcnow().isoformat()+"Z",
    "projection": params,
    "features": features
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f)

print("Saved:", OUTPUT_JSON)
print("DONE.")
