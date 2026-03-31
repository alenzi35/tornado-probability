import os
import urllib.request
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime

INPUT_CSV = "map/data/1hr_samples.csv"
OUTPUT_CSV = "map/data/rap_tornado_samples.csv"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

df = pd.read_csv(INPUT_CSV)

samples = []

# ================= VARIABLE PICKER =================

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
            if not (abs(g.bottomLevel-bottom) < 1 and abs(g.topLevel-top) < 1):
                continue

        return g

    raise RuntimeError(f"{shortname} not found")

# ================= LOOP THROUGH TORNADOES =================

for _, row in df.iterrows():

    dt = datetime.strptime(f"{row['Date']} {row['Valid time']}", "%b %d %Y %H:%M")

    date = dt.strftime("%Y%m%d")
    hour = dt.strftime("%H")

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"
    local_file = f"{DATA_DIR}/rap_{date}_{hour}.grib2"

    if not os.path.exists(local_file):
        print("Downloading", url)
        urllib.request.urlretrieve(url, local_file)

    print("Processing", local_file)

    grbs = pygrib.open(local_file)

    # ================= VARIABLES =================

    grbs.seek(0)
    cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    cin_msg = pick_var(grbs, "cin", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

    grbs.seek(0)
    t2m_msg = pick_var(grbs, "2t", "heightAboveGround", level=2)

    grbs.seek(0)
    d2m_msg = pick_var(grbs, "2d", "heightAboveGround", level=2)

    grbs.seek(0)
    u10_msg = pick_var(grbs, "10u", "heightAboveGround", level=10)

    grbs.seek(0)
    v10_msg = pick_var(grbs, "10v", "heightAboveGround", level=10)

    grbs.seek(0)
    u500_msg = pick_var(grbs, "u", "isobaricInhPa", level=500)

    grbs.seek(0)
    v500_msg = pick_var(grbs, "v", "isobaricInhPa", level=500)

    # ================= ARRAYS =================

    cape = np.nan_to_num(cape_msg.values)
    cin = np.nan_to_num(cin_msg.values)
    hlcy = np.nan_to_num(hlcy_msg.values)

    t2m = np.nan_to_num(t2m_msg.values)
    d2m = np.nan_to_num(d2m_msg.values)

    u10 = np.nan_to_num(u10_msg.values)
    v10 = np.nan_to_num(v10_msg.values)

    u500 = np.nan_to_num(u500_msg.values)
    v500 = np.nan_to_num(v500_msg.values)

    lats, lons = cape_msg.latlons()

    # ================= FIND NEAREST GRID CELL =================

    dist = (lats - row["Latitude"])**2 + (lons - row["Longitude"])**2
    i, j = np.unravel_index(np.argmin(dist), dist.shape)

    samples.append({

        "datetime": dt,
        "latitude": row["Latitude"],
        "longitude": row["Longitude"],

        "CAPE": float(cape[i,j]),
        "CIN": float(cin[i,j]),
        "SRH": float(hlcy[i,j]),

        "T2M": float(t2m[i,j]),
        "D2M": float(d2m[i,j]),

        "U10": float(u10[i,j]),
        "V10": float(v10[i,j]),

        "U500": float(u500[i,j]),
        "V500": float(v500[i,j]),

        "tornado": 1

    })

# ================= SAVE =================

out = pd.DataFrame(samples)
out.to_csv(OUTPUT_CSV, index=False)

print("Saved:", OUTPUT_CSV)
print("Tornado samples:", len(out))
