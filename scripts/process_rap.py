import pygrib
import numpy as np
import json
from pyproj import CRS, Transformer

# ---------------- MOCK GRIB DATA ----------------
# For demonstration, we'll create a tiny 5x5 grid
rows, cols = 5, 5
# Normally you would use: lats, lons = cape_msg.latlons()
# For demo, let's use lat 35-40, lon -100 to -95
lats = np.linspace(35, 40, rows).reshape(rows, 1) + np.zeros((rows, cols))
lons = np.linspace(-100, -95, cols).reshape(1, cols) + np.zeros((rows, cols))

# Dummy probability data
prob = np.random.rand(rows, cols)

# ---------------- DEFINE LCC PROJECTION ----------------
# Example Lambert Conformal Conic (U.S. continental RAP-like)
proj_params = {
    "proj": "lcc",
    "lat_1": 38.5,
    "lat_2": 38.5,
    "lat_0": 38.5,
    "lon_0": -97,
    "x_0": 0,
    "y_0": 0,
    "datum": "WGS84",
    "units": "m",
    "no_defs": True
}

crs_lcc = CRS(proj_params)
crs_wgs = CRS.from_epsg(4326)
transformer = Transformer.from_crs(crs_wgs, crs_lcc, always_xy=True)

# ---------------- PROJECT LAT/LON TO LCC ----------------
flat_lons = lons.flatten()
flat_lats = lats.flatten()
flat_x, flat_y = transformer.transform(flat_lons, flat_lats)
xx = np.array(flat_x).reshape(rows, cols)
yy = np.array(flat_y).reshape(rows, cols)

# ---------------- WRITE JSON ----------------
features = []
for i in range(rows):
    for j in range(cols):
        features.append({
            "x": float(xx[i,j]),
            "y": float(yy[i,j]),
            "prob": float(prob[i,j])
        })

output_json = {"projection": proj_params, "features": features}

with open("tornado_prob_lcc_test.json", "w") as f:
    json.dump(output_json, f, indent=2)

print("Test JSON written: tornado_prob_lcc_test.json")
