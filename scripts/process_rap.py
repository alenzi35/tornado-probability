import os
import urllib.request
import numpy as np
import pygrib
import json
from datetime import datetime, timedelta

# ----------------------------
# 1. RAP GRIB setup
# ----------------------------
today = datetime.utcnow().date()
target_hour = 21  # target UTC hour
forecast_init_hour = (target_hour - 2) % 24  # 2 hours behind

# RAP URL and local path
rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{today:%Y%m%d}/rap.t{forecast_init_hour:02d}z.awp130pgrbf02.grib2"
local_path = f"data/rap_{today:%Y%m%d}_t{forecast_init_hour:02d}z_f02.grib2"
os.makedirs("data", exist_ok=True)

# Download GRIB if missing
if not os.path.exists(local_path):
    print(f"Downloading RAP GRIB from {rap_url} ...")
    urllib.request.urlretrieve(rap_url, local_path)
    print("Download complete.")
else:
    print("RAP GRIB already exists locally.")

# ----------------------------
# 2. Open GRIB and inspect variables
# ----------------------------
print("\nInspecting variables in GRIB...")

grbs = pygrib.open(local_path)

def find_variable_by_level_range(grbs, varname, level_min=None, level_max=None):
    """
    Find the first message for varname within optional numeric level range.
    If level_min/max are None, just pick the first available message.
    """
    candidates = [g for g in grbs if g.shortName == varname]
    if not candidates:
        raise RuntimeError(f"{varname} NOT FOUND in GRIB!")
    
    for g in candidates:
        lvl = getattr(g, "level", None)
        if lvl is not None:
            if ((level_min is None or lvl >= level_min) and
                (level_max is None or lvl <= level_max)):
                print(f"{varname}: using level {lvl} ({g.typeOfLevel})")
                return g
    # fallback: pick first candidate if no level in range
    g = candidates[0]
    print(f"{varname}: preferred level range not found, using level {getattr(g,'level','?')} ({g.typeOfLevel})")
    return g

# CAPE & CIN: 0–90 mb if possible, HLCY: 0–1000 m
CAPE_msg = find_variable_by_level_range(grbs, "CAPE", 0, 90)
CIN_msg  = find_variable_by_level_range(grbs, "CIN", 0, 90)
HLCY_msg = find_variable_by_level_range(grbs, "HLCY", 0, 1000)

CAPE = CAPE_msg.values
CIN  = CIN_msg.values
HLCY = HLCY_msg.values

grbs.close()
print("✅ CAPE, CIN, HLCY extracted successfully.")

# ----------------------------
# 3. Compute 1-hour tornado probability
# ----------------------------
intercept = -1.5686
coeffs = {
    "CAPE": 2.88592370e-03,
    "CIN": 2.38728498e-05,
    "HLCY": 8.85192696e-03
}

def logistic_prob(cape, cin, hlcy):
    z = intercept + coeffs["CAPE"]*cape + coeffs["CIN"]*cin + coeffs["HLCY"]*hlcy
    return 1 / (1 + np.exp(-z))

prob_grid = logistic_prob(CAPE, CIN, HLCY)

# ----------------------------
# 4. Save probability as JSON
# ----------------------------
output = {
    "date": str(today),
    "target_hour_utc": target_hour,
    "probability_grid": prob_grid.tolist()
}

output_path = "data/tornado_prob.json"
with open(output_path, "w") as f:
    json.dump(output, f)

print(f"\nTornado probabilities saved to {output_path}")
