import os
import json
import urllib.request
from datetime import datetime, timedelta
import pygrib
import numpy as np

# -------------------------------
# 1️⃣ Setup directories and target times
# -------------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Example: target forecast 21:00 UTC today
target_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
init_time = target_time - timedelta(hours=2)  # RAP initialized 2h before
fhr = 2  # forecast hour to hit target

date_str = init_time.strftime("%Y%m%d")
hour_str = init_time.strftime("%H")

rap_filename = f"rap.t{hour_str}z.awp130pgrbf{fhr:02d}.grib2"
rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date_str}/{rap_filename}"
grib_path = os.path.join(DATA_DIR, rap_filename)

# -------------------------------
# 2️⃣ Download GRIB if missing
# -------------------------------
if not os.path.exists(grib_path):
    print(f"Downloading RAP GRIB: {rap_url}")
    urllib.request.urlretrieve(rap_url, grib_path)
    print("Download complete.")
else:
    print("RAP GRIB already exists:", grib_path)

# -------------------------------
# 3️⃣ Open GRIB and detect variables
# -------------------------------
grbs = pygrib.open(grib_path)

CAPE_msg = None
CIN_msg = None
HLCY_msg = None

print("\nInspecting variables in GRIB:")
for grb in grbs:
    print(f"{grb.shortName}: typeOfLevel={grb.typeOfLevel}")
    if grb.shortName == "CAPE":
        CAPE_msg = grb
    elif grb.shortName == "CIN":
        CIN_msg = grb
    elif grb.shortName in ["HLCY","SRH"]:  # HLCY is sometimes SRH
        HLCY_msg = grb

grbs.close()

# -------------------------------
# 4️⃣ Check that all variables were found
# -------------------------------
if not CAPE_msg or not CIN_msg or not HLCY_msg:
    raise RuntimeError("CAPE, CIN, or HLCY not found in GRIB file!")

print("\n✅ All required variables found. Proceeding to probability calculation.")

# -------------------------------
# 5️⃣ Read data arrays
# -------------------------------
# We convert to 2D numpy arrays
grbs = pygrib.open(grib_path)
CAPE = np.array([g.values for g in grbs if g == CAPE_msg])[0]
CIN = np.array([g.values for g in grbs if g == CIN_msg])[0]
HLCY = np.array([g.values for g in grbs if g == HLCY_msg])[0]
grbs.close()

# -------------------------------
# 6️⃣ Compute 1-hour tornado probability
# -------------------------------
# Coefficients
intercept = -1.5686
coef_CAPE = 2.88592370e-03
coef_CIN = 2.38728498e-05
coef_HLCY = 8.85192696e-03

logit = intercept + coef_CAPE*CAPE + coef_CIN*CIN + coef_HLCY*HLCY
prob = 1 / (1 + np.exp(-logit))

# -------------------------------
# 7️⃣ Save probability JSON for map
# -------------------------------
output = {
    "lead_time_hours": 1,
    "valid_time": target_time.strftime("%H:%M"),
    "probabilities": prob.tolist()
}

output_path = os.path.join(DATA_DIR, "tornado_prob.json")
with open(output_path, "w") as f:
    json.dump(output, f)

print(f"\n✅ Tornado probability saved to {output_path}")
