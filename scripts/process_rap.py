import os
import urllib.request
from datetime import datetime, timedelta

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

# Download if missing
if not os.path.exists(grib_path):
    print(f"Downloading RAP GRIB: {rap_url}")
    urllib.request.urlretrieve(rap_url, grib_path)
    print("Download complete.")
else:
    print("RAP GRIB already exists:", grib_path)
