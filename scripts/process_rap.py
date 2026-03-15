import os
import json
import requests
from datetime import datetime
import pygrib
import numpy as np

OUT_JSON = "map/data/tornado_prob_lcc.json"
TMP_GRIB = "rap.grib2"

# -------------------------------
# RAP URL
# -------------------------------

now = datetime.utcnow()
date_str = now.strftime("%Y%m%d")
run_hour = now.hour

url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date_str}/rap.t{run_hour:02d}z.awip32f01.grib2"

print(f"Target: {date_str} {run_hour:02d} F01")
print("URL:", url)

# -------------------------------
# Download GRIB
# -------------------------------

r = requests.get(url)
r.raise_for_status()

with open(TMP_GRIB, "wb") as f:
    f.write(r.content)

print("Downloaded RAP GRIB2")

grbs = pygrib.open(TMP_GRIB)

# -------------------------------
# Variable extractor
# -------------------------------

def pick_var(grbs, shortName, typeOfLevel=None, level=None, bottomLevel=None, topLevel=None):

    for g in grbs:

        if g.shortName != shortName:
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None and g.level != level:
            continue

        if bottomLevel is not None and getattr(g, "bottomLevel", None) != bottomLevel:
            continue

        if topLevel is not None and getattr(g, "topLevel", None) != topLevel:
            continue

        return g

    raise RuntimeError(
        f"Variable not found: shortName={shortName}, typeOfLevel={typeOfLevel}, level={level}, bottomLevel={bottomLevel}, topLevel={topLevel}"
    )

# -------------------------------
# Extract variables
# -------------------------------

cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer", level=18000)
cin_msg  = pick_var(grbs, "cin",  "pressureFromGroundLayer", level=18000)

hlcy_msg = pick_var(
    grbs,
    "hlcy",
    "heightAboveGroundLayer",
    bottomLevel=0,
    topLevel=1000
)

t2_msg  = pick_var(grbs, "2t",  "heightAboveGround", level=2)
td2_msg = pick_var(grbs, "2d",  "heightAboveGround", level=2)

u10_msg = pick_var(grbs, "10u", "heightAboveGround", level=10)
v10_msg = pick_var(grbs, "10v", "heightAboveGround", level=10)

u500_msg = pick_var(grbs, "u", "isobaricInhPa", level=500)
v500_msg = pick_var(grbs, "v", "isobaricInhPa", level=500)

# -------------------------------
# Grid + projection
# -------------------------------

lats, lons = cape_msg.latlons()
projparams = cape_msg.projparams

dx = cape_msg["DxInMetres"]
dy = cape_msg["DyInMetres"]

# -------------------------------
# Values
# -------------------------------

cape = cape_msg.values
cin  = cin_msg.values
hlcy = hlcy_msg.values

t2  = t2_msg.values
td2 = td2_msg.values

u10 = u10_msg.values
v10 = v10_msg.values

u500 = u500_msg.values
v500 = v500_msg.values

# -------------------------------
# Derived parameters
# -------------------------------

lcl = (t2 - td2) * 125

shear = np.sqrt((u500 - u10)**2 + (v500 - v10)**2)

# -------------------------------
# Build cells
# -------------------------------

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

            "lcl": float(lcl[j, i]),
            "shear": float(shear[j, i])
        })

# -------------------------------
# Save JSON with projection
# -------------------------------

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
