import os
import pygrib
import urllib.request
import numpy as np
import pandas as pd
import datetime
import requests

# ================= CONFIG =================
OUTPUT_CSV = "map/data/rap_non_tornado_samples.csv"
os.makedirs("map/data", exist_ok=True)

# ================= NON-TORNADO DATES =================
NON_TORNADO_DATES = [
    ("2025-06-21", "16"),
    ("2025-07-02", "22"),
    ("2025-08-25", "18"),
    ("2025-10-08", "15")
]

# ================= RAP DOWNLOAD URL =================
def rap_url(date, hour):
    ymd = date.replace("-", "")
    return f"https://noaa-rap-pds.s3.amazonaws.com/rap.{ymd}/rap.t{hour}z.awp130bgrbf00.grib2"

# ================= VARIABLE PICKER =================
def pick_var(grbs, shortname, typeOfLevel=None, level=None, bottom=None, top=None):
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

# ================= PROCESS GRIB =================
def process_grib(grib_file):
    print("Processing", grib_file)
    grbs = pygrib.open(grib_file)

    # ------------------ Extract variables ------------------
    cape = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000).values
    cin  = pick_var(grbs, "cin",  "pressureFromGroundLayer", 0, 9000).values
    srh  = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000).values

    t2m  = pick_var(grbs, "2t", "heightAboveGround", level=2).values
    d2m  = pick_var(grbs, "2d", "heightAboveGround", level=2).values

    # Compute LCL (approximation)
    lcl = (t2m - d2m) * 125.0

    u10  = pick_var(grbs, "10u", "heightAboveGround", level=10).values
    v10  = pick_var(grbs, "10v", "heightAboveGround", level=10).values

    u500 = pick_var(grbs, "u", "isobaricInhPa", level=500).values
    v500 = pick_var(grbs, "v", "isobaricInhPa", level=500).values

    shear = np.sqrt((u500-u10)**2 + (v500-v10)**2)  # approx 0-6km shear

    rows, cols = cape.shape
    samples = []

    for i in range(rows):
        for j in range(cols):
            samples.append({
                "CAPE": float(cape[i,j]),
                "CIN": float(cin[i,j]),
                "SRH": float(srh[i,j]),
                "LCL": float(lcl[i,j]),
                "Shear": float(shear[i,j])
            })

    return samples

# ================= MAIN =================
all_samples = []

for date, hour in NON_TORNADO_DATES:
    url = rap_url(date, hour)
    local_file = f"data/rap_{date.replace('-','')}_{hour}00.grib2"

    if not os.path.exists(local_file):
        print("Downloading", url)
        urllib.request.urlretrieve(url, local_file)
    else:
        print("Using cached", local_file)

    samples = process_grib(local_file)
    all_samples.extend(samples)

# ================= SAVE CSV =================
df = pd.DataFrame(all_samples)
df.to_csv(OUTPUT_CSV, index=False)
print("Saved non-tornado samples to:", OUTPUT_CSV)
print("Total samples:", len(df))
