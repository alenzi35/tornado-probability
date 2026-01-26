import os
import urllib.request
import cfgrib
from datetime import datetime, timedelta

# ============================================================
# USER SETTING — TARGET TIME (UTC)
# Monday 26 Jan 2026, 21:00 UTC
# ============================================================
target_time = datetime(2026, 1, 26, 21, 0)

# ============================================================
# RAP TIMING LOGIC
# RAP forecast initialized 2 hours before target
# ============================================================
init_time = target_time - timedelta(hours=2)

forecast_hour = int((target_time - init_time).total_seconds() / 3600)
forecast_hour_str = f"{forecast_hour:02d}"

date_str = init_time.strftime("%Y%m%d")
hour_str = init_time.strftime("%H")

# ============================================================
# REAL NOAA RAP URL (THIS WAS THE PROBLEM BEFORE)
# ============================================================
rap_url = (
    f"https://noaa-rap-pds.s3.amazonaws.com/"
    f"rap.{date_str}/rap.t{hour_str}z.awp130pgrbf{forecast_hour_str}.grib2"
)

print("RAP URL:", rap_url)

# ============================================================
# DOWNLOAD GRIB
# ============================================================
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)

grib_file = os.path.join(
    data_dir,
    f"rap_{date_str}_t{hour_str}z_f{forecast_hour_str}.grib2"
)

if not os.path.exists(grib_file):
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(rap_url, grib_file)
    print("Download complete.")
else:
    print("GRIB already exists:", grib_file)

# ============================================================
# VARIABLE CHECK — THIS ANSWERS YOUR CORE QUESTION
# ============================================================
variables = [
    # CAPE: 0–90 mb isobaric
    {
        "name": "CAPE",
        "shortName": "CAPE",
        "typeOfLevel": "isobaricInhPa",
    },
    # CIN: 0–90 mb isobaric
    {
        "name": "CIN",
        "shortName": "CIN",
        "typeOfLevel": "isobaricInhPa",
    },
    # Storm-relative helicity (HLCY): 0–1000 m AGL
    {
        "name": "HLCY",
        "shortName": "HLCY",
        "typeOfLevel": "heightAboveGround",
    },
]

print("\nInspecting variables:\n")

for var in variables:
    try:
        ds = cfgrib.open_dataset(
            grib_file,
            filter_by_keys={
                "shortName": var["shortName"],
                "typeOfLevel": var["typeOfLevel"],
            },
        )
        print(f"{var['name']} ✅ FOUND")
        print(f"  dimensions: {list(ds.dims)}")
        print(f"  coordinates: {list(ds.coords)}\n")

    except Exception as e:
        print(f"{var['name']} ❌ NOT FOUND")
        print(f"  error: {e}\n")

print("DONE")
