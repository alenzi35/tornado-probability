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
# 2. Open GRIB and extract variables
# ----------------------------
print("\nInspecting variables in GRIB...")

grbs = pygrib.open(local_path)

def pick_grib_message(grbs, varname, preferred_levels):
    """Pick the first message matching preferred_levels, fallback to any message if needed."""
    for lvl in preferred_levels:
        msgs = [g for g in grbs if g.shortName == varname and g.typeOfLevel == lvl]
        if msgs:
            print(f"{varname}: using level {lvl}")
            return msgs[0]
    # fallback: pick first message with that variable
    msgs = [g for g in grbs if g.shortName == varname]
    if msgs:
        print(f"{varname}: preferred levels not found, using {msgs[0].typeOfLevel}")
        return msgs[0]
    raise RuntimeError(f"{varname} NOT FOUND in any candidate levels!")

# CAPE & CIN: preferred pressureFromGroundLayer (0–90 mb), HLCY: heightAboveGroundLayer (0–1000 m AG)
CAPE_msg = pick_grib_message(grbs, "CAPE", ["pressureFromGroundLayer"])
CIN_msg  = pick_grib_message(grbs, "CIN", ["pressureFromGroundLayer"])
HLCY_msg = pick_grib_message(grbs, "HLCY", ["heightAboveGroundLayer"])

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
