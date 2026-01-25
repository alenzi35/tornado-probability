import os
from datetime import datetime, timedelta
import boto3
from botocore import UNSIGNED
from botocore.client import Config
import cfgrib

# ----------------------------
# CONFIG
# ----------------------------
BUCKET = "noaa-rap-pds"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ----------------------------
# TIME LOGIC (same as before)
# ----------------------------
now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
target_time = now
init_time = target_time - timedelta(hours=2)

cycle_hour = init_time.strftime("%H")
cycle_date = init_time.strftime("%Y%m%d")

print(f"Target time: {target_time}")
print(f"Using RAP init: {init_time}Z")

# ----------------------------
# S3 PATH
# ----------------------------
s3_key = f"rap.{cycle_date}/rap.t{cycle_hour}z.awp130pgrbf00.grib2"
local_file = os.path.join(DATA_DIR, "rap_latest.grib2")

print(f"S3 key: {s3_key}")

# ----------------------------
# DOWNLOAD
# ----------------------------
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
s3.download_file(BUCKET, s3_key, local_file)
print("Downloaded RAP file successfully")

# ----------------------------
# INSPECT GRIB MESSAGES
# ----------------------------
print("\n--- INSPECTING CAPE / CIN / SRH GRIB MESSAGES ---\n")

gribs = cfgrib.open_file(local_file)

for var in gribs.variables.values():
    a = var.attributes
    if a.get("shortName") in ["cape", "cin", "hlcy"]:
        print(
            f"shortName={a.get('shortName')}, "
            f"typeOfLevel={a.get('typeOfLevel')}, "
            f"level={a.get('level')}, "
            f"stepType={a.get('stepType')}, "
            f"forecastTime={a.get('forecastTime')}"
        )

print("\n--- END INSPECTION ---")
