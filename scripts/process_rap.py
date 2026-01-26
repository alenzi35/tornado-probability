import os
import cfgrib
import urllib.request
from datetime import datetime, timedelta

# ----------------- USER: set your target UTC time -----------------
# Example: Monday, 26 Jan 2026, 21:00 UTC
target_time = datetime(2026, 1, 26, 21, 0)

# ----------------- RAP initialization logic -----------------
# RAP needs forecast initialized 2 hours before target
init_time = target_time - timedelta(hours=2)

# Forecast hour = difference between target and init
forecast_hour = int((target_time - init_time).total_seconds() / 3600)
forecast_hour_str = f"{forecast_hour:02d}"  # e.g., 2 -> "02"

# Format init time for filename
date_str = init_time.strftime("%Y%m%d")  # e.g., 20260126
hour_str = init_time.strftime("%H")      # e.g., "19"

# ----------------- Construct RAP URL -----------------
# Replace with the actual NOAA RAP S3 endpoint
rap_url = f"https://noaa-rap-bucket/rap.{date_str}/{hour_str}/rap.t{hour_str}z.awp130pgrbf{forecast_hour_str}.grib2"
print("RAP URL:", rap_url)

# ----------------- Download GRIB -----------------
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
grib_file = os.path.join(data_dir, f"rap_{date_str}_{hour_str}_f{forecast_hour_str}.grib2")

if not os.path.exists(grib_file):
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(rap_url, grib_file)
    print("Download complete.")
else:
    print("GRIB file already exists locally:", grib_file)

# ----------------- Check CAPE/CIN/HLCY -----------------
variables = [
    {"name": "CAPE", "shortName": "CAPE", "level": "isobaricInhPa", "min": 0, "max": 90},
    {"name": "CIN", "shortName": "CIN", "level": "isobaricInhPa", "min": 0, "max": 90},
    {"name": "HLCY", "shortName": "HLCY", "level": "heightAboveGround", "min": 0, "max": 1000},
]

all_present = True

for var in variables:
    try:
        ds = cfgrib.open_dataset(
            grib_file,
            filter_by_keys={"shortName": var["shortName"], "typeOfLevel": var["level"]}
        )
        levels = ds.get(var["level"])
        if levels is not None:
            in_range = any((levels >= var["min"]) & (levels <= var["max"]))
            if in_range:
                print(f"{var['name']} ✅ exists at desired level")
            else:
                print(f"{var['name']} ❌ exists but not in desired range")
                all_present = False
        else:
            print(f"{var['name']} ❌ loaded but no level info")
            all_present = False
    except Exception as e:
        print(f"{var['name']} ❌ could not be read: {e}")
        all_present = False

print("\nAll variables present:", all_present)
