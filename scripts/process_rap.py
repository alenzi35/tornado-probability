import subprocess
import sys

# ------------------ Install packages ------------------
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "xarray", "cfgrib", "requests"])

import requests
import xarray as xr
import os

# ------------------ CONFIG ------------------
DATE = "20260312"
HOUR = "21"
FCST = "01"

LOCAL_GRIB = "data/rap_inspect.grib2"
URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

os.makedirs(os.path.dirname(LOCAL_GRIB), exist_ok=True)

# ------------------ DOWNLOAD ------------------
print("Downloading:", URL)
r = requests.get(URL)
r.raise_for_status()

with open(LOCAL_GRIB, "wb") as f:
    f.write(r.content)
print("Saved to:", LOCAL_GRIB)
print()

# ------------------ INSPECT ------------------
print("Opening GRIB2 with cfgrib/xarray…")

ds = xr.open_dataset(LOCAL_GRIB, engine="cfgrib")

print("Variables found in the GRIB2 file:\n")
for var in ds.variables:
    if var in ds.coords:
        continue
    da = ds[var]
    name = da.attrs.get("long_name", "")
    level_type = da.attrs.get("GRIB_typeOfLevel", "")
    level = da.attrs.get("GRIB_level", "")
    print(f"{var:<15} | {name:<45} | levelType={level_type} level={level}")

print("\n=== End of variable list ===")
