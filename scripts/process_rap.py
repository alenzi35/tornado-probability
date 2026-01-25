import os
import json
from datetime import datetime, timedelta
import numpy as np
import xarray as xr
import boto3
from botocore import UNSIGNED
from botocore.client import Config

# ----------------------------
# CONFIG
# ----------------------------
BUCKET = "noaa-rap-pds"
DATA_DIR = "data"
FORECAST_OFFSET_HOURS = 2  # target valid time minus init time

os.makedirs(DATA_DIR, exist_ok=True)

# ----------------------------
# TIME LOGIC
# ----------------------------
# Target valid time = current hour
now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
target_time = now

# RAP init = target - 2 hours
init_time = target_time - timedelta(hours=FORECAST_OFFSET_HOURS)
cycle_hour = init_time.strftime("%H")
cycle_date = init_time.strftime("%Y%m%d")

print(f"Target time: {target_time}")
print(f"Using RAP init: {init_time}Z")

# ----------------------------
# S3 FILE PATH
# ----------------------------
# Example: rap.20260125/rap.t12z.awp130pgrbf00.grib2
s3_key = f"rap.{cycle_date}/rap.t{cycle_hour}z.awp130pgrbf00.grib2"
local_file = os.path.join(DATA_DIR, "rap_latest.grib2")

print(f"S3 key: {s3_key}")

# ----------------------------
# DOWNLOAD FILE
# ----------------------------
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
s3.download_file(BUCKET, s3_key, local_file)
print("Downloaded RAP file successfully")

# ----------------------------
# OPEN & EXTRACT DATA (placeholder field)
# ----------------------------
ds = xr.open_dataset(local_file, engine="cfgrib")

# Use first variable as placeholder
var_name = list(ds.data_vars)[0]
field = ds[var_name].values

# ----------------------------
# GRID PROBABILITY CALCULATION (dummy)
# ----------------------------
# For demo: average and normalize to max 0.006
prob_value = float(np.clip(np.mean(field)/np.max(field), 0, 0.006))

# ----------------------------
# SAVE JSON FOR WEBSITE
# ----------------------------
output = {
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "cycle_utc": init_time.isoformat() + "Z",
    "forecast_hour": FORECAST_OFFSET_HOURS,
    "valid_utc": target_time.isoformat() + "Z",
    "probability": round(prob_value, 5)
}

json_file = os.path.join(DATA_DIR, "tornado_prob.json")
with open(json_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Saved JSON: {json_file}")
