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
# Example: forecast initialized at 2 hours before target
target_hour = 21  # target UTC hour
forecast_init_hour = (target_hour - 2) % 24

# Build RAP URL
rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{today:%Y%m%d}/rap.t{forecast_init_hour:02d}z.awp130pgrbf02.grib2"
local_path = f"data/rap_{today:%Y%m%d}_t{forecast_init_hour:02d}z_f02.grib2"
os.makedirs("data", exist_ok=True)

# Download if missing
if not os.path.exists(local_path):
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(rap_url, local_path)
    print("Download complete.")
else:
    print("RAP GRIB already exists locally.")

# ----------------------------
# 2. Open GRIB and extract variables
# ----------------------------
print("\nInspecting variables in GRIB...")

grbs = pygrib.open(local_path)

# Pick correct levels
try:
    CAPE_msg = [g for g in grbs if g.shortName=="CAPE" and g.typeOfLevel=="pressureFromGroundLayer"][0]
    CIN_msg  = [g for g in grbs if g.shortName=="CIN"  and g.typeOfLevel=="pressureFromGroundLayer"][0]
    HLCY_msg = [g for g in grbs if g.shortName=="HLCY" and g.typeOfLevel=="heightAboveGroundLayer"][0]
except IndexError:
    raise RuntimeError("One of CAPE, CIN, or HLCY not found at desired levels!")

CAPE = CAPE_msg.values
CIN  = CIN_msg.values
HLCY = HLCY_msg.values

grbs.close()

print("✅ CAPE, CIN, HLCY extracted successfully.")

# ----------------------------
# 3. Compute 1-hour tornado probability
# ----------------------------
# Your coefficients
intercept = -1.5686
coeffs = {
    "CAPE": 2.88592370e-03,
    "CIN": 2.38728498e-05,
    "HLCY": 8.85192696e-03
}

# Logistic probability function
def logistic_prob(cape, cin, hlcy):
    z = intercept + coeffs["CAPE"]*cape + coeffs["CIN"]*cin + coeffs["HLCY"]*hlcy
    return 1 / (1 + np.exp(-z))

# Compute probability grid
prob_grid = logistic_prob(CAPE, CIN, HLCY)

# ----------------------------
# 4. Save as JSON
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
