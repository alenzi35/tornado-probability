import os
import urllib.request
import pygrib
import numpy as np
import json
from pyproj import CRS, Transformer

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

GRIB_PATH = "data/rap.grib2"
OUT_LCC = "map/data/tornado_prob_lcc.json"
OUT_LATLON = "map/data/tornado_prob.json"

# Logistic regression coefficients
INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# ---------------- SETUP ----------------
os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- DOWNLOAD ----------------
print("Downloading RAP...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete.")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

# ---------------- PICK VARIABLE ----------------
def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        print(f"Found {shortname}")
        return g
    raise RuntimeError(f"{shortname} not found")

# ---------------- LOAD DATA ----------------
grbs.seek(0)
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")
grbs.seek(0)
cin_msg = pick_var(grbs, "cin", typeOfLevel="surface")
grbs.seek(0)
hlcy_msg = pick_var(grbs, "hlcy", typeOfLevel="heightAboveGroundLayer", bottom=0, top=1000)

cape = np.nan_to_num(cape_msg.values, nan=0.0)
cin = np.nan_to_num(cin_msg.values, nan=0.0)
hlcy = np.nan_to_num(hlcy_msg.values, nan=0.0)

rows, cols = cape.shape

# ---------------- GRID GEOMETRY (LCC) ----------------
proj_params = cape_msg.projparams

# Manually build LCC CRS
lcc_crs = CRS.from_proj4(
    f"""
    +proj=lcc
    +lat_1={proj_params['lat_1']}
    +lat_2={proj_params['lat_2']}
    +lat_0={proj_params['lat_0']}
    +lon_0={proj_params['lon_0']}
    +a={proj_params['a']}
    +b={proj_params['b']}
    +units=m
    +no_defs
    """
)
wgs84 = CRS.from_epsg(4326)
to_latlon = Transformer.from_crs(lcc_crs, wgs84, always_xy=True)

# Estimate dx/dy from GRIB grid
lat_vals, lon_vals = cape_msg.latlons()
dx = float(np.mean(np.diff(lon_vals[0, :])))  # degrees longitude spacing
dy = float(np.mean(np.diff(lat_vals[:, 0])))  # degrees latitude spacing

# Convert degrees to meters roughly for native grid
dx_m = dx * 111320  # approximate meters per degree
dy_m = dy * 111320

print(f"Estimated grid spacing (m): dx={dx_m:.1f}, dy={dy_m:.1f}")

# ---------------- BUILD NATIVE LCC GRID ----------------
# Build x/y coordinates manually
x_vals = np.arange(cols) * dx_m
y_vals = np.arange(rows) * dy_m
xs, ys = np.meshgrid(x_vals, y_vals)

# Center around 0,0 (optional, consistent with previous LCC JSON)
xs = xs - np.mean(xs)
ys = ys - np.mean(ys)

# ---------------- PROBABILITY ----------------
linear = INTERCEPT + COEFFS["CAPE"] * cape + COEFFS["CIN"] * cin + COEFFS["HLCY"] * hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- BUILD OUTPUT ----------------
lcc_features = []
latlon_features = []

for i in range(rows):
    for j in range(cols):
        x = float(xs[i, j])
        y = float(ys[i, j])
        p = float(prob[i, j])

        # LCC native
        lcc_features.append({
            "x": x,
            "y": y,
            "dx": dx_m,
            "dy": dy_m,
            "prob": p
        })

        # Lat/Lon
        lon, lat = to_latlon.transform(x, y)
        latlon_features.append({
            "lat": lat,
            "lon": lon,
            "dLat": dy,
            "dLon": dx,
            "prob": p
        })

# ---------------- WRITE JSON ----------------
with open(OUT_LCC, "w") as f:
    json.dump({"projection": proj_params, "features": lcc_features}, f)
print("Wrote:", OUT_LCC)

with open(OUT_LATLON, "w") as f:
    json.dump(latlon_features, f)
print("Wrote:", OUT_LATLON)

print("Points:", len(lcc_features))
print("Processing complete.")
