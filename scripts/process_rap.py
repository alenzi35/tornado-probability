import os
import json
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import xarray as xr

# =========================
# CONFIG
# =========================

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 1-hour tornado probability model (YOUR coefficients)
INTERCEPT = -1.5686
COEF_CAPE = 2.88592370e-03
COEF_CIN  = 2.38728498e-05
COEF_HLCY = 8.85192696e-03

# =========================
# DETERMINE RAP FILE
# =========================

now = datetime.utcnow()

# RAP availability logic:
# forecast initialized 2 hours before target time
init_time = now - timedelta(hours=2)
fhr = 2  # forecast hour offset

date_str = init_time.strftime("%Y%m%d")
hour_str = init_time.strftime("%H")

rap_filename = f"rap.t{hour_str}z.awp130pgrbf{fhr:02d}.grib2"
rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date_str}/{rap_filename}"

grib_path = os.path.join(DATA_DIR, rap_filename)

print(f"RAP URL: {rap_url}")

# =========================
# DOWNLOAD RAP
# =========================

if not os.path.exists(grib_path):
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(rap_url, grib_path)
    print("Download complete.")
else:
    print("RAP GRIB already exists.")

# =========================
# LOAD VARIABLES
# =========================

print("\nInspecting variables:\n")

# --- CAPE & CIN (atmosphereSingleLayer diagnostics) ---
ds_diag = xr.open_dataset(
    grib_path,
    engine="cfgrib",
    filter_by_keys={"typeOfLevel": "atmosphereSingleLayer"}
)

if "CAPE" not in ds_diag:
    raise RuntimeError("CAPE NOT FOUND (atmosphereSingleLayer)")

if "CIN" not in ds_diag:
    raise RuntimeError("CIN NOT FOUND (atmosphereSingleLayer)")

cape = ds_diag["CAPE"].values
cin  = ds_diag["CIN"].values

print("CAPE ✅ FOUND")
print("CIN  ✅ FOUND")

# --- HLCY / SRH (0–1000 m AGL) ---
ds_hlcy = xr.open_dataset(
    grib_path,
    engine="cfgrib",
    filter_by_keys={"typeOfLevel": "heightAboveGround"}
)

if "HLCY" not in ds_hlcy:
    raise RuntimeError("HLCY (SRH) NOT FOUND at 0–1000 m AGL")

hlcy = ds_hlcy["HLCY"].values

print("HLCY ✅ FOUND")

# =========================
# PROBABILITY CALCULATION
# =========================

print("\nComputing tornado probability...")

# Logistic regression
logit = (
    INTERCEPT
    + COEF_CAPE * cape
    + COEF_CIN  * cin
    + COEF_HLCY * hlcy
)

prob = 1 / (1 + np.exp(-logit))
prob = np.clip(prob, 0, 1)

# =========================
# EXPORT FOR MAP
# =========================

output = {
    "generated_utc": now.isoformat() + "Z",
    "forecast_valid_utc": (init_time + timedelta(hours=fhr)).isoformat() + "Z",
    "probability": prob.tolist(),
}

out_path = os.path.join(DATA_DIR, "tornado_prob.json")

with open(out_path, "w") as f:
    json.dump(output, f)

print(f"\nDONE — tornado_prob.json written")
