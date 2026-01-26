import boto3
from botocore import UNSIGNED
from botocore.client import Config
import datetime as dt
import os
import numpy as np
import xarray as xr
import json

# ----------------------------
# CONFIG
# ----------------------------
BUCKET = "noaa-rap-pds"
DATA_DIR = "data"
FORECAST_OFFSET_HOURS = 2

os.makedirs(DATA_DIR, exist_ok=True)

# Variables with their correct typeOfLevel
VARIABLES = [
    {"shortName": "CAPE", "typeOfLevel": "isobaricInhPa"},
    {"shortName": "CIN", "typeOfLevel": "isobaricInhPa"},
    {"shortName": "HLCY", "typeOfLevel": "heightAboveGround"}
]

# ----------------------------
# Time logic
# ----------------------------
now = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
target_time = now
init_time = target_time - dt.timedelta(hours=FORECAST_OFFSET_HOURS)

cycle = init_time.strftime("%H")
date = init_time.strftime("%Y%m%d")

print(f"Target time: {target_time}")
print(f"Using RAP init: {init_time}Z")

# ----------------------------
# RAP file path
# ----------------------------
key = f"rap.{date}/rap.t{cycle}z.awp130pgrbf00.grib2"
print(f"S3 key: {key}")

# ----------------------------
# Download RAP file
# ----------------------------
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
local_file = os.path.join(DATA_DIR, "rap_latest.grib2")

try:
    s3.download_file(BUCKET, key, local_file)
    print("Downloaded RAP file")
except Exception as e:
    print(f"Failed to download RAP file: {e}")
    exit(1)

# ----------------------------
# Load variables safely
# ----------------------------
data_dict = {}
for var in VARIABLES:
    try:
        ds_var = xr.open_dataset(local_file, engine="cfgrib",
                                 filter_by_keys=var)
        if len(ds_var.data_vars) == 0:
            print(f"Warning: {var['shortName']} not in this GRIB file")
            continue
        name = list(ds_var.data_vars)[0]
        data_dict[var["shortName"]] = ds_var[name].values
        print(f"Loaded {var['shortName']} ({var['typeOfLevel']})")
    except Exception as e:
        print(f"Failed to load {var['shortName']}: {e}")

# ----------------------------
# Create 10x10 probability grid (placeholder calculation)
# ----------------------------
grid = np.zeros((10, 10))
for i in range(10):
    for j in range(10):
        vals = []
        if "CAPE" in data_dict:
            vals.append(np.mean(data_dict["CAPE"][i::10, j::10])/1000)
        if "CIN" in data_dict:
            vals.append(np.clip(np.abs(np.mean(data_dict["CIN"][i::10, j::10]))/100, 0,1))
        if "HLCY" in data_dict:
            vals.append(np.mean(data_dict["HLCY"][i::10, j::10])/500)
        if vals:
            grid[i,j] = np.clip(sum(vals), 0,1)
        else:
            grid[i,j] = 0

# ----------------------------
# Save JSON
# ----------------------------
out = {
    "target_time": target_time.isoformat() + "Z",
    "init_time": init_time.isoformat() + "Z",
    "probability_grid": grid.tolist()
}

json_file = os.path.join(DATA_DIR, "tornado_prob.json")
with open(json_file, "w") as f:
    json.dump(out, f, indent=2)

print(f"Saved {json_file}")
