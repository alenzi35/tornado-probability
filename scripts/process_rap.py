import subprocess
import sys

# ------------------ Install cfgrib at runtime ------------------
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "cfgrib", "requests"])

import os
import requests
import cfgrib

# ------------------ CONFIG ------------------
DATE = "20260312"
HOUR = "21"
FCST = "01"

LOCAL_GRIB = f"data/rap_inspect.grib2"
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

# ------------------ INSPECT VARIABLES ------------------
print("Inspecting GRIB2 messages…")

from cfgrib import open_file

with open_file(LOCAL_GRIB) as f:
    for i, msg in enumerate(f.messages, start=1):
        name = getattr(msg, "name", "")
        shortName = getattr(msg, "shortName", "")
        typeOfLevel = getattr(msg, "typeOfLevel", "")
        level = getattr(msg, "level", "")
        bottomLevel = getattr(msg, "bottomLevel", "")
        topLevel = getattr(msg, "topLevel", "")
        print(f"{i:03d}: shortName={shortName:<10} name={name:<45} typeOfLevel={typeOfLevel:<25} level={level} bottomLevel={bottomLevel} topLevel={topLevel}")

print("\n=== End of GRIB2 messages ===")
