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

# Optional: specify variable you actually want
# Example: {"shortName":"CAPE", "typeOfLevel":"surface"} or {}
VARIABLE_FILTER = {}  # empty = pick first variable automatically

os.makedirs(DATA_DIR, exist_ok=True)

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
# Load GRIB with variable filter
# ----------------------------
try:
    ds = xr.open_dataset(local_file, engine="cfgrib", filter_by_keys=VARIABLE_FILTER)
except Exception as e:
    print(f"Failed to open GRIB file: {e}")
    exit(1)

# Pick first variable if filter returned multiple
var = list(ds.data_vars)[0]
data = ds[var].values

# Placeholder probability calculation
prob = float(np.clip(np.mean(data) / np.max(data), 0, 1))

# ----------------------------
# Save JSON for website
# ----------------------------
out = {
    "target_time": target_time.isoformat() + "Z",
    "init_time": init_time.isoformat() + "Z",
    "probability": prob
}

json_file = os.path.join(DATA_DIR, "tornado_prob.json")
with open(json_file, "w") as f:
    json.dump(out, f, indent=2)

print(f"Saved {json_file}")
