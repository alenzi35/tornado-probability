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

            if not (
                abs(g.bottomLevel - bottom) < 1 and
                abs(g.topLevel - top) < 1
            ):
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
hlcy_msg = pick_var(
    grbs,
    "hlcy",
    typeOfLevel="heightAboveGroundLayer",
    bottom=0,
    top=1000
)


cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values


# ---------------- GRID GEOMETRY (LCC) ----------------

# Get projection info from GRIB
proj_params = cape_msg.projparams
lcc_crs = CRS.from_cf(proj_params)
wgs84 = CRS.from_epsg(4326)

# Transformer LCC → lat/lon
to_latlon = Transformer.from_crs(
    lcc_crs,
    wgs84,
    always_xy=True
)

# Get native x/y grid
xs, ys = cape_msg.xy()

# Grid spacing (meters)
dx = np.mean(np.diff(xs[0, :]))
dy = np.mean(np.diff(ys[:, 0]))

print("Grid spacing (m):", dx, dy)


# ---------------- CLEAN NaNs ----------------

cape = np.nan_to_num(cape, nan=0.0)
cin  = np.nan_to_num(cin, nan=0.0)
hlcy = np.nan_to_num(hlcy, nan=0.0)


# ---------------- PROBABILITY ----------------

linear = (
    INTERCEPT +
    COEFFS["CAPE"] * cape +
    COEFFS["CIN"]  * cin +
    COEFFS["HLCY"] * hlcy
)

prob = 1 / (1 + np.exp(-linear))


# ---------------- BUILD OUTPUT ----------------

rows, cols = prob.shape

lcc_features = []
latlon_features = []


print("Building grids...")

for i in range(rows):
    for j in range(cols):

        x = float(xs[i, j])
        y = float(ys[i, j])
        p = float(prob[i, j])

        # Convert to lat/lon from LCC
        lon, lat = to_latlon.transform(x, y)

        # Native LCC
        lcc_features.append({
            "x": x,
            "y": y,
            "dx": float(dx),
            "dy": float(dy),
            "prob": p
        })

        # Lat/Lon (derived from same grid)
        latlon_features.append({
            "lat": float(lat),
            "lon": float(lon),
            "dLat": float(abs(dy / 111320)),  # approx meters→deg
            "dLon": float(abs(dx / (111320 * np.cos(np.radians(lat))))),
            "prob": p
        })


# ---------------- WRITE LCC JSON ----------------

lcc_out = {
    "projection": proj_params,
    "features": lcc_features
}

with open(OUT_LCC, "w") as f:
    json.dump(lcc_out, f)

print("Wrote:", OUT_LCC)


# ---------------- WRITE LAT/LON JSON ----------------

with open(OUT_LATLON, "w") as f:
    json.dump(latlon_features, f)

print("Wrote:", OUT_LATLON)


# ---------------- DONE ----------------

print("Points:", len(lcc_features))
print("LCC size:", os.path.getsize(OUT_LCC), "bytes")
print("LatLon size:", os.path.getsize(OUT_LATLON), "bytes")
print("Processing complete.")
