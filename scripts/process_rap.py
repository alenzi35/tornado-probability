import os
import urllib.request
import pygrib

# ---------------- CONFIG ----------------
DATE_STR = "20260128"
HOUR_STR = "19"
FCST = "02"

# Path to store the GRIB
GRIB_PATH = "data/rap.grib2"
os.makedirs("data", exist_ok=True)

# URL of RAP GRIB file (same as your target)
RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE_STR}/rap.t{HOUR_STR}z.awp130pgrbf{FCST}.grib2"

# ---------------- DOWNLOAD ----------------
print("Downloading:", RAP_URL)
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

# ---------------- INSPECT CAPE/CIN VARIABLES ----------------
print("\n---- CAPE/CIN/HLCSY INVENTORY ----\n")
for i, g in enumerate(grbs):
    name = g.shortName.lower()
    if "cape" in name or "cin" in name or "hlcy" in name:
        print(f"Message #{i+1}")
        print(f"  shortName    : {g.shortName}")
        print(f"  name         : {g.name}")
        print(f"  typeOfLevel  : {g.typeOfLevel}")
        if g.typeOfLevel == "heightAboveGroundLayer":
            print(f"  bottomLevel  : {g.bottomLevel} m")
            print(f"  topLevel     : {g.topLevel} m")
        elif g.typeOfLevel == "pressureLayer":
            print(f"  bottomLevel  : {g.bottomLevel} hPa")
            print(f"  topLevel     : {g.topLevel} hPa")
        elif g.typeOfLevel == "surface":
            pass  # surface has no additional info
        print(f"  values shape : {g.values.shape}")
        print("-" * 40)

# Reset GRIB pointer
grbs.seek(0)

print("\nDone inspecting GRIB file.\n")
