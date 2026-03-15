import os
import json
import requests
from datetime import datetime
import pygrib
import numpy as np

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

OUT_JSON = "map/data/tornado_prob_lcc.json"
TMP_GRIB = "rap.grib2"

# -------------------------------------------------
# Determine latest RAP run
# -------------------------------------------------

now = datetime.utcnow()
run_hour = now.hour
date_str = now.strftime("%Y%m%d")

url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date_str}/rap.t{run_hour:02d}z.awip32f01.grib2"

print(f"Target: {date_str} {run_hour:02d} F01")
print("URL:", url)

# -------------------------------------------------
# Download GRIB
# -------------------------------------------------

r = requests.get(url)
r.raise_for_status()

with open(TMP_GRIB, "wb") as f:
    f.write(r.content)

print("Downloaded RAP GRIB2")

# -------------------------------------------------
# Open GRIB
# -------------------------------------------------

grbs = pygrib.open(TMP_GRIB)

# -------------------------------------------------
# Helper function to extract variables
# -------------------------------------------------

def pick_var(grbs, shortName, typeOfLevel=None, level=None):

    for g in grbs:

        if g.shortName != shortName:
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None and g.level != level:
            continue

        return g

    raise RuntimeError(
        f"Variable not found: shortName={shortName}, typeOfLevel={typeOfLevel}, level={level}"
    )


# -------------------------------------------------
# Extract variables (exact list you gave)
# -------------------------------------------------

cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer", 18000)
cin_msg = pick_var(grbs, "cin", "pressureFromGroundLayer", 18000)

hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 1000)

t2_msg = pick_var(grbs, "2t", "heightAboveGround", 2)
td2_msg = pick_var(grbs, "2d", "heightAboveGround", 2)

u10_msg = pick_var(grbs, "10u", "heightAboveGround", 10)
v10_msg = pick_var(grbs, "10v", "heightAboveGround", 10)

u500_msg = pick_var(grbs, "u", "isobaricInhPa", 500)
v500_msg = pick_var(grbs, "v", "isobaricInhPa", 500)

# -------------------------------------------------
# Get grid + projection
# -------------------------------------------------

lats, lons = cape_msg.latlons()

projparams = cape_msg.projparams

dx = cape_msg["DxInMetres"]
dy = cape_msg["DyInMetres"]

# -------------------------------------------------
# Extract values
# -------------------------------------------------

cape = cape_msg.values
cin = cin_msg.values
hlcy = hlcy_msg.values

t2 = t2_msg.values
td2 = td2_msg.values

u10 = u10_msg.values
v10 = v10_msg.values

u500 = u500_msg.values
v500 = v500_msg.values

# -------------------------------------------------
# Example derived calculations
# -------------------------------------------------

# LCL (approx)
lcl = (t2 - td2) * 125

# Shear magnitude
shear = np.sqrt((u500 - u10) ** 2 + (v500 - v10) ** 2)

# -------------------------------------------------
# Build output cells
# -------------------------------------------------

features = []

ny, nx = cape.shape

for j in range(ny):
    for i in range(nx):

        features.append({
            "x": float(i * dx),
            "y": float(j * dy),
            "dx": float(dx),
            "dy": float(dy),

            "cape": float(cape[j, i]),
            "cin": float(cin[j, i]),
            "hlcy": float(hlcy[j, i]),

            "t2": float(t2[j, i]),
            "td2": float(td2[j, i]),

            "shear": float(shear[j, i]),
            "lcl": float(lcl[j, i])
        })

# -------------------------------------------------
# Save JSON (WITH projection)
# -------------------------------------------------

output = {
    "projection": {
        "lat_1": projparams["lat_1"],
        "lat_2": projparams["lat_2"],
        "lat_0": projparams["lat_0"],
        "lon_0": projparams["lon_0"],
        "a": projparams.get("a", 6371229),
        "b": projparams.get("b", 6371229)
    },
    "features": features
}

os.makedirs("map/data", exist_ok=True)

with open(OUT_JSON, "w") as f:
    json.dump(output, f)

print("Saved:", OUT_JSON)
print("Total cells:", len(features))
