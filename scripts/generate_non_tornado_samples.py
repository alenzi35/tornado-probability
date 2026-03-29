import os
import urllib.request
import pygrib
import numpy as np
import pandas as pd
import datetime
import requests

# ================= CONFIG =================
DATA_DIR = "data"
OUTPUT_CSV = "map/data/rap_non_tornado_samples.csv"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= NON-TORNADO TIMES =================
non_tornado_times = [
    {"date":"20250825","hour":"18"},
]

FCST = "01"  # 1-hour lead time

# ================= PICK VAR FUNCTION (from process_rap.py) =================
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
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        return g
    raise RuntimeError(f"{shortname} not found")

# ================= PROCESS EACH DATE/HOUR =================
all_samples = []

for dt in non_tornado_times:
    DATE = dt["date"]
    HOUR = dt["hour"]

    print(f"\nProcessing RAP for {DATE} {HOUR}z")

    RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
    local_file = f"{DATA_DIR}/rap_{DATE}_{HOUR}z_f{FCST}.grib2"

    # Download if not already present
    if not os.path.isfile(local_file):
        print(f"Downloading {RAP_URL}")
        urllib.request.urlretrieve(RAP_URL, local_file)
        print("Download complete")
    else:
        print("File already exists")

    # Open GRIB
    grbs = pygrib.open(local_file)

    # Extract variables (same as process_rap.py)
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

    # Derived variables
    lcl = (t2m - d2m) * 125  # simple approximation
    shear = np.sqrt((u500 - u10)**2 + (v500 - v10)**2)

    # Flatten grids and append to list
    nrows, ncols = cape.shape
    for i in range(nrows):
        for j in range(ncols):
            all_samples.append({
                "date": DATE,
                "hour": HOUR,
                "i": i,
                "j": j,
                "cape": cape[i,j],
                "cin": cin[i,j],
                "hlcy": hlcy[i,j],
                "t2m": t2m[i,j],
                "d2m": d2m[i,j],
                "lcl": lcl[i,j],
                "u10": u10[i,j],
                "v10": v10[i,j],
                "u500": u500[i,j],
                "v500": v500[i,j],
                "shear": shear[i,j],
                "tornado": 0
            })

    grbs.close()
    print(f"Added {nrows*ncols} cells for {DATE} {HOUR}z")

# ================= SAVE CSV =================
df = pd.DataFrame(all_samples)
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved non-tornado samples to {OUTPUT_CSV}")
print("DONE.")
