import requests
import xarray as xr
import sys
import os

# ================= CONFIG =================

# **Set actual date/hour/forecast**
DATE = "20260312"
HOUR = "22"
FCST = "01"

# Download path
LOCAL_GRIB = "data/rap_inspect.grib2"

URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

print("Downloading:", URL)

# Download the file
os.makedirs(os.path.dirname(LOCAL_GRIB), exist_ok=True)

r = requests.get(URL)
if r.status_code != 200:
    print("Failed to download file:", r.status_code, r.text[:200])
    sys.exit(1)

with open(LOCAL_GRIB, "wb") as f:
    f.write(r.content)

print("Saved to:", LOCAL_GRIB)
print()

# ================= INSPECT USING CFGRIB =================

print("Opening with cfgrib… (may take a moment)\n")

try:
    ds = xr.open_dataset(LOCAL_GRIB, engine="cfgrib")
except Exception as e:
    print("Error opening GRIB:", e)
    sys.exit(1)

print("Dataset variables found:\n")

for var in ds.variables:
    # skip coordinate-like metadata if too noisy
    if var in ds.coords:
        continue
    da = ds[var]
    name = da.attrs.get("long_name", "")
    level = da.attrs.get("GRIB_level", "")
    level_type = da.attrs.get("GRIB_typeOfLevel", "")
    print(f"{var:<15} | {name:<45} | level: {level_type} {level}")

print("\n=== End of variable list ===")
