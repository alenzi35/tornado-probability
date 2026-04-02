import os
import urllib.request
import pygrib
import numpy as np
import pandas as pd
from datetime import datetime

# ================= CONFIG =================

DATA_DIR = "data"
INPUT_CSV = "map/data/1hr_samples.csv"
OUTPUT_CSV = "map/data/rap_tornado_samples.csv"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

FCST = "01"

df = pd.read_csv(INPUT_CSV)

samples = []

# ================= PICK VAR FUNCTION =================

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


# ================= PROCESS EACH TORNADO =================

for idx, row in df.iterrows():

    try:

        dt = datetime.strptime(f"{row['Date']} {row['Valid time']}", "%b %d %Y %H:%M")

        DATE = dt.strftime("%Y%m%d")
        HOUR = dt.strftime("%H")

        print(f"\nProcessing tornado {idx+1}/{len(df)}  {DATE} {HOUR}z")

        RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
        local_file = f"{DATA_DIR}/rap_{DATE}_{HOUR}z_f{FCST}.grib2"

        if not os.path.isfile(local_file):
            print("Downloading", RAP_URL)
            urllib.request.urlretrieve(RAP_URL, local_file)

        grbs = pygrib.open(local_file)

        # ================= VARIABLES =================

        grbs.seek(0)
        cape = np.nan_to_num(pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000).values)

        grbs.seek(0)
        cin = np.nan_to_num(pick_var(grbs, "cin", "pressureFromGroundLayer", 0, 9000).values)

        grbs.seek(0)
        hlcy = np.nan_to_num(pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000).values)

        grbs.seek(0)
        t2m = np.nan_to_num(pick_var(grbs, "2t", "heightAboveGround", level=2).values)

        grbs.seek(0)
        d2m = np.nan_to_num(pick_var(grbs, "2d", "heightAboveGround", level=2).values)

        grbs.seek(0)
        u10 = np.nan_to_num(pick_var(grbs, "10u", "heightAboveGround", level=10).values)

        grbs.seek(0)
        v10 = np.nan_to_num(pick_var(grbs, "10v", "heightAboveGround", level=10).values)

        grbs.seek(0)
        u500 = np.nan_to_num(pick_var(grbs, "u", "isobaricInhPa", level=500).values)

        grbs.seek(0)
        v500 = np.nan_to_num(pick_var(grbs, "v", "isobaricInhPa", level=500).values)

        # ================= DERIVED VARIABLES =================

        lcl = (t2m - d2m) * 125
        shear = np.sqrt((u500 - u10)**2 + (v500 - v10)**2)

        lats, lons = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000).latlons()

        # ================= FIND NEAREST GRID CELL =================

        dist = (lats - row["Latitude"])**2 + (lons - row["Longitude"])**2
        i, j = np.unravel_index(np.argmin(dist), dist.shape)

        sample = {

            "date": DATE,
            "hour": HOUR,

            "lat": row["Latitude"],
            "lon": row["Longitude"],

            "cape": cape[i,j],
            "cin": cin[i,j],
            "hlcy": hlcy[i,j],

            "t2m": t2m[i,j],
            "d2m": d2m[i,j],

            "lcl": lcl[i,j],
            "shear": shear[i,j],

            "tornado": 1
        }

        samples.append(sample)

        grbs.close()

        # ================= SAVE PROGRESS EVERY SAMPLE =================

        pd.DataFrame(samples).to_csv(OUTPUT_CSV, index=False)

        print("Saved sample", idx+1)

    except Exception as e:

        print("ERROR processing row", idx)
        print(e)

        continue


# ================= FINAL SAVE =================

out = pd.DataFrame(samples)
out.to_csv(OUTPUT_CSV, index=False)

print("\nFINAL SAVE:", os.path.abspath(OUTPUT_CSV))
print("Total samples:", len(out))
