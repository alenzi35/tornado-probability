import os
import urllib.request
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime

# ================= CONFIG =================

INPUT_CSV = "map/data/tornado_spatiotemporal.csv"
OUTPUT_CSV = "map/data/rap_tornado_samples.csv"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ================= LOAD TORNADO CSV =================

df = pd.read_csv(INPUT_CSV)

samples = []

# ================= GRIB VARIABLE PICKER =================

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel-bottom)<1 and abs(g.topLevel-top)<1):
                continue
        return g
    raise RuntimeError(f"{shortname} not found")

# ================= MAIN LOOP =================

for _, row in df.iterrows():

    dt = datetime.strptime(f"{row['Date']} {row['Valid time']}", "%Y-%m-%d %H:%M")

    date = dt.strftime("%Y%m%d")
    hour = dt.strftime("%H")

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"
    local_file = f"{DATA_DIR}/rap_{date}_{hour}.grib2"

    if not os.path.exists(local_file):
        print("Downloading", url)
        urllib.request.urlretrieve(url, local_file)

    print("Processing", local_file)

    grbs = pygrib.open(local_file)

    grbs.seek(0)
    cape_msg = pick_var(grbs, "cape", "surface")

    grbs.seek(0)
    cin_msg = pick_var(grbs, "cin", "surface")

    grbs.seek(0)
    srh_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

    cape = cape_msg.values
    cin = cin_msg.values
    srh = srh_msg.values

    lats, lons = cape_msg.latlons()

    # ================= FIND NEAREST GRID CELL =================

    dist = (lats - row["Latitude"])**2 + (lons - row["Longitude"])**2
    i, j = np.unravel_index(np.argmin(dist), dist.shape)

    sample = {
        "datetime": dt,
        "latitude": row["Latitude"],
        "longitude": row["Longitude"],
        "CAPE": float(cape[i,j]),
        "CIN": float(cin[i,j]),
        "SRH": float(srh[i,j]),
        "tornado": 1
    }

    samples.append(sample)

# ================= SAVE =================

out = pd.DataFrame(samples)
out.to_csv(OUTPUT_CSV, index=False)

print("Saved tornado samples:", OUTPUT_CSV)
print("Total samples:", len(out))
