import os
import json
from datetime import datetime, timedelta

import boto3
import numpy as np
import pygrib
from botocore import UNSIGNED
from botocore.client import Config

# ----------------------------
# CONFIG
# ----------------------------
BUCKET = "noaa-rap-pds"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Logistic regression (1-hour)
INTERCEPT = -1.5686
B_CAPE = 2.88592370e-03
B_CIN  = 2.38728498e-05
B_SRH  = 8.85192696e-03

# ----------------------------
# TIME LOGIC
# ----------------------------
now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
target_time = now
init_time = target_time - timedelta(hours=2)

cycle_date = init_time.strftime("%Y%m%d")
cycle_hour = init_time.strftime("%H")

print(f"Target UTC: {target_time}")
print(f"RAP init: {init_time}Z")

# ----------------------------
# DOWNLOAD RAP GRIB
# ----------------------------
s3_key = f"rap.{cycle_date}/rap.t{cycle_hour}z.awp130pgrbf00.grib2"
local_file = os.path.join(DATA_DIR, "rap_latest.grib2")

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
s3.download_file(BUCKET, s3_key, local_file)

print("Downloaded RAP GRIB")

# ----------------------------
# OPEN GRIB
# ----------------------------
grbs = pygrib.open(local_file)

# ---- CAPE 0–90 mb ----
cape_msg = grbs.select(
    name="Convective available potential energy",
    typeOfLevel="pressureFromGroundLayer"
)[0]
cape = cape_msg.values

# ---- CIN 0–90 mb ----
cin_msg = grbs.select(
    name="Convective inhibition",
    typeOfLevel="pressureFromGroundLayer"
)[0]
cin = cin_msg.values

# ---- SRH 0–1 km ----
srh_msg = grbs.select(
    name="Storm relative helicity",
    typeOfLevel="heightAboveGroundLayer"
)[0]
srh = srh_msg.values

lats, lons = cape_msg.latlons()
grbs.close()

print("Extracted CAPE, CIN, SRH")

# ----------------------------
# LOGISTIC REGRESSION
# ----------------------------
z = (
    INTERCEPT
    + B_CAPE * cape
    + B_CIN  * cin
    + B_SRH  * srh
)

prob = 1 / (1 + np.exp(-z))
prob = np.clip(prob, 0, 1)

# ----------------------------
# AGGREGATE TO YOUR MAP CELLS
# ----------------------------
lat_step = 1.18
lon_step = 1.94

lat_bins = np.arange(24.5, 49.5, lat_step)
lon_bins = np.arange(-125, -66.5, lon_step)

aggregates = []

for lat0 in lat_bins:
    for lon0 in lon_bins:
        mask = (
            (lats >= lat0) & (lats < lat0 + lat_step) &
            (lons >= lon0) & (lons < lon0 + lon_step)
        )

        if np.any(mask):
            p = float(np.mean(prob[mask]))
            aggregates.append({
                "lat": float(lat0),
                "lng": float(lon0),
                "probability": p
            })

# ----------------------------
# SAVE JSON
# ----------------------------
output = {
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "valid_utc": target_time.isoformat() + "Z",
    "rap_init_utc": init_time.isoformat() + "Z",
    "lead_hours": 1,
    "aggregates": aggregates
}

out_file = os.path.join(DATA_DIR, "tornado_prob.json")
with open(out_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Wrote {out_file}")
