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
from shapely.geometry import Point
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
    "HLCY": 0.008318690761993085,
    "DEPR": -0.0045
}

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= TIME LOGIC =================

def get_target_cycle():
    now = datetime.datetime.utcnow()
    run_time = now - datetime.timedelta(hours=1)
    date = run_time.strftime("%Y%m%d")
    hour = run_time.strftime("%H")
    return date, hour

DATE, HOUR = get_target_cycle()
FCST = "01"

# ================= DOWNLOAD RAP 32km =================

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

print("Target:", DATE, HOUR, "F01")
print("URL:", RAP_URL)

def url_exists(url):
    r = requests.head(url)
    return r.status_code == 200

if not url_exists(RAP_URL):
    print("RAP file not ready yet. Skipping.")
    exit(0)

urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Downloaded RAP GRIB2")

# ================= LOAD GRIB =================

grbs = pygrib.open(GRIB_PATH)

def pick_var(shortName=None, typeOfLevel=None, level=None, topLevel=None):

    for g in grbs:

        if shortName and g.shortName != shortName:
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None:

            if hasattr(g, "level"):
                if g.level != level:
                    continue

            if hasattr(g, "bottomLevel"):
                if g.bottomLevel != level:
                    continue

        if topLevel is not None:

            if not hasattr(g, "topLevel"):
                continue

            if g.topLevel != topLevel:
                continue

        return g

    raise RuntimeError(
        f"{shortName} {typeOfLevel} {level} {topLevel} not found"
    )

# ================= CORE VARIABLES =================

grbs.seek(0)
cape_msg = pick_var("cape")

grbs.seek(0)
cin_msg = pick_var("cin")

grbs.seek(0)
hlcy_msg = pick_var("hlcy", "heightAboveGroundLayer", 0, 1000)

# ================= NEW EXTRACTIONS =================

grbs.seek(0)
t2_msg = pick_var("2t", "heightAboveGround", 2)

grbs.seek(0)
d2_msg = pick_var("2d", "heightAboveGround", 2)

grbs.seek(0)
u10_msg = pick_var("10u", "heightAboveGround", 10)

grbs.seek(0)
v10_msg = pick_var("10v", "heightAboveGround", 10)

grbs.seek(0)
u500_msg = pick_var("u", "isobaricInhPa", 500)

grbs.seek(0)
v500_msg = pick_var("v", "isobaricInhPa", 500)

# ================= ARRAYS =================

cape = np.nan_to_num(cape_msg.values)
cin = np.nan_to_num(cin_msg.values)
hlcy = np.nan_to_num(hlcy_msg.values)

t2 = np.nan_to_num(t2_msg.values)
d2 = np.nan_to_num(d2_msg.values)

depr = t2 - d2

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

logit = (
    INTERCEPT
    + COEFFS["CAPE"] * cape
    + COEFFS["CIN"] * cin
    + COEFFS["HLCY"] * hlcy
    + COEFFS["DEPR"] * depr
)

prob = 1 / (1 + np.exp(-logit))

# ================= LOAD CONUS =================

print("Downloading CONUS shapefile...")

r = requests.get(CONUS_SHAPE_URL)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall(DATA_DIR)

shp_path = None

for f in os.listdir(DATA_DIR):
    if f.endswith(".shp"):
        shp_path = os.path.join(DATA_DIR, f)
        break

states = gpd.read_file(shp_path)

exclude = ["AK", "HI", "PR", "GU", "VI", "MP", "AS"]

states = states[~states["STUSPS"].isin(exclude)]

conus = states.unary_union
prepared = prep(conus)

# ================= GRID FILTER =================

ny, nx = prob.shape

dx = x_vals[0,1] - x_vals[0,0]
dy = y_vals[1,0] - y_vals[0,0]

features = []

for i in range(ny):
    for j in range(nx):

        p = float(prob[i,j])

        if p < 0.02:
            continue

        lon = lons[i,j]
        lat = lats[i,j]

        if not prepared.contains(Point(lon, lat)):
            continue

        x = x_vals[i,j]
        y = y_vals[i,j]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [x - dx/2, y - dy/2],
                    [x + dx/2, y - dy/2],
                    [x + dx/2, y + dy/2],
                    [x - dx/2, y + dy/2],
                    [x - dx/2, y - dy/2]
                ]]
            },
            "properties": {"p": p}
        })

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(geojson, f)

print("Saved tornado probability GeoJSON")

# ================= PROOF EXTRACTION =================

print("Extraction check:")
print("T2:", t2.shape)
print("Td2:", d2.shape)
print("U10:", u10.shape)
print("V10:", v10.shape)
print("U500:", u500.shape)
print("V500:", v500.shape)
