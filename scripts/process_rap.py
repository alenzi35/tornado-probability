import os
import json
from datetime import datetime, timedelta
import numpy as np
import xarray as xr
import cfgrib
import boto3
from botocore import UNSIGNED
from botocore.client import Config

# ----------------------------
# CONFIG
# ----------------------------
BUCKET = "noaa-rap-pds"
DATA_DIR = "data"
FORECAST_OFFSET_HOURS = 2  # RAP init = target - 2h

os.makedirs(DATA_DIR, exist_ok=True)

# Logistic regression coefficients (replace with your real ones)
COEFS = {
    "cape": 0.0005,       # placeholder
    "cin": -0.0003,       # placeholder
    "srh": 0.0012,        # placeholder
    "intercept": -4.0     # placeholder
}

# ----------------------------
# TIME LOGIC
# ----------------------------
now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
target_time = now
init_time = target_time - timedelta(hours=FORECAST_OFFSET_HOURS)

cycle_hour = init_time.strftime("%H")
cycle_date = init_time.strftime("%Y%m%d")

print(f"Target time: {target_time}")
print(f"Using RAP init: {init_time}Z")

# ----------------------------
# S3 FILE PATH
# ----------------------------
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
# FIND VARIABLES AUTOMATICALLY
# ----------------------------
grib_vars = cfgrib.open_file(local_file).variables
print("Available GRIB variables:")
for k in grib_vars.keys():
    print(k)

# Function to pick a variable containing certain keywords
def find_var(keywords):
    for k in grib_vars.keys():
        for kw in keywords:
            if kw.lower() in k.lower():
                return k
    raise ValueError(f"No variable found for keywords {keywords}")

cape_var = find_var(["cape", "0to90"])     # 0–90mb CAPE
cin_var  = find_var(["cin", "0to90"])      # 0–90mb CIN
srh_var  = find_var(["srh", "0to1"])      # 0–1km SRH

print(f"Using variables: CAPE={cape_var}, CIN={cin_var}, SRH={srh_var}")

# ----------------------------
# EXTRACT VARIABLES
# ----------------------------
def extract_var(var_name):
    ds = xr.open_dataset(
        local_file,
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"shortName": var_name}}
    )
    return ds[list(ds.data_vars)[0]].values

cape = extract_var(cape_var)
cin  = extract_var(cin_var)
srh  = extract_var(srh_var)

# Flatten arrays
cape_flat = cape.flatten()
cin_flat  = cin.flatten()
srh_flat  = srh.flatten()

# ----------------------------
# LOGISTIC REGRESSION
# ----------------------------
def logistic_prob(cape, cin, srh):
    z = (COEFS["cape"] * cape +
         COEFS["cin"] * cin +
         COEFS["srh"] * srh +
         COEFS["intercept"])
    p = 1 / (1 + np.exp(-z))
    return np.clip(p, 0, 1)

probabilities = logistic_prob(cape_flat, cin_flat, srh_flat)
prob_grid = probabilities.reshape(cape.shape)

# ----------------------------
# AGGREGATE CELLS (1°x2° example)
# ----------------------------
lat_step = 1.18
lng_step = 1.94
lat_min, lat_max = 24.5, 49.5
lng_min, lng_max = -125, -66.5

aggregates = []
grid_shape = cape.shape

lats = np.arange(lat_min, lat_max, lat_step)
lngs = np.arange(lng_min, lng_max, lng_step)

for lat in lats:
    for lng in lngs:
        lat_idx = int((lat - lat_min) / (lat_max - lat_min) * grid_shape[0])
        lng_idx = int((lng - lng_min) / (lng_max - lng_min) * grid_shape[1])
        prob = prob_grid[lat_idx, lng_idx]
        aggregates.append({
            "lat": lat,
            "lng": lng,
            "probability": float(prob)
        })

# ----------------------------
# SAVE JSON
# ----------------------------
output = {
    "generated_utc": datetime.utcnow().isoformat() + "Z",
    "cycle_utc": init_time.isoformat() + "Z",
    "forecast_hour": FORECAST_OFFSET_HOURS,
    "valid_utc": target_time.isoformat() + "Z",
    "aggregates": aggregates
}

json_file = os.path.join(DATA_DIR, "tornado_prob.json")
with open(json_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Saved JSON: {json_file}")
