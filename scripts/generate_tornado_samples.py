import os
import urllib.request
import pandas as pd
import numpy as np
import pygrib
from datetime import datetime

DATA_DIR = "data"
TORNADO_CSV = "map/data/1hr_samples.csv"
OUTPUT_CSV = "map/data/rap_tornado_samples.csv"

os.makedirs(DATA_DIR, exist_ok=True)


# ===============================
# RAP DOWNLOAD
# ===============================

def download_rap(date, hour):

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"
    local_file = f"{DATA_DIR}/rap_{date}_{hour}.grib2"

    if not os.path.exists(local_file):
        print("Downloading", url)
        urllib.request.urlretrieve(url, local_file)

    return local_file


# ===============================
# SAME PICK_VAR FUNCTION YOU USE
# ===============================

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None, level=None):

    for g in grbs:

        if g.shortName.lower() != shortname.lower():
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None and hasattr(g, "level"):
            if abs(g.level - level) > 0.1:
                continue

        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel-bottom)<1 and abs(g.topLevel-top)<1):
                continue

        return g

    raise RuntimeError(f"{shortname} not found")


# ===============================
# LOAD TORNADO LIST
# ===============================

tornado_df = pd.read_csv(TORNADO_CSV)

samples = []

# ===============================
# LOOP THROUGH TORNADOES
# ===============================

for _, row in tornado_df.iterrows():

    dt = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M")

    date = dt.strftime("%Y%m%d")
    hour = dt.strftime("%H")

    lat = row["lat"]
    lon = row["lon"]

    grib_file = download_rap(date, hour)

    print("Processing", grib_file)

    grbs = pygrib.open(grib_file)

    # --- variables (same as working script)

    grbs.seek(0)
    cape = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    cin = pick_var(grbs, "cin", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    hlcy = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

    grbs.seek(0)
    t2m = pick_var(grbs, "2t", "heightAboveGround", level=2)

    grbs.seek(0)
    d2m = pick_var(grbs, "2d", "heightAboveGround", level=2)

    grbs.seek(0)
    u10 = pick_var(grbs, "10u", "heightAboveGround", level=10)

    grbs.seek(0)
    v10 = pick_var(grbs, "10v", "heightAboveGround", level=10)

    grbs.seek(0)
    u500 = pick_var(grbs, "u", "isobaricInhPa", level=500)

    grbs.seek(0)
    v500 = pick_var(grbs, "v", "isobaricInhPa", level=500)

    # grid
    lats, lons = cape.latlons()

    # find nearest grid cell
    dist = (lats-lat)**2 + (lons-lon)**2
    i,j = np.unravel_index(dist.argmin(), dist.shape)

    samples.append({

        "cape": float(cape.values[i,j]),
        "cin": float(cin.values[i,j]),
        "hlcy": float(hlcy.values[i,j]),

        "t2m": float(t2m.values[i,j]),
        "d2m": float(d2m.values[i,j]),

        "u10": float(u10.values[i,j]),
        "v10": float(v10.values[i,j]),

        "u500": float(u500.values[i,j]),
        "v500": float(v500.values[i,j]),

        "tornado": 1
    })


# ===============================
# SAVE DATASET
# ===============================

df = pd.DataFrame(samples)

df.to_csv(OUTPUT_CSV, index=False)

print("Saved tornado samples:", OUTPUT_CSV)
print("Total:", len(df))
