# ------------------ INSTALL pygrib ------------------
import sys
import subprocess

try:
    import pygrib
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygrib"])
    import pygrib

# ------------------ IMPORTS ------------------
import os
import urllib.request

# ------------------ CONFIG ------------------
DATE = "20260312"
HOUR = "21"
FCST = "01"

LOCAL_GRIB = f"data/rap_inspect.grib2"
URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

os.makedirs(os.path.dirname(LOCAL_GRIB), exist_ok=True)

# ------------------ DOWNLOAD ------------------
print("Downloading:", URL)
urllib.request.urlretrieve(URL, LOCAL_GRIB)
print("Saved to:", LOCAL_GRIB)
print()

# ------------------ INSPECT ------------------
print("Inspecting GRIB2 messages…")

grbs = pygrib.open(LOCAL_GRIB)
for i, g in enumerate(grbs, start=1):
    print(f"{i:03d}: shortName={g.shortName:<10} "
          f"name={g.name:<45} "
          f"typeOfLevel={g.typeOfLevel:<25} "
          f"level={getattr(g,'level','')} "
          f"bottomLevel={getattr(g,'bottomLevel','')} "
          f"topLevel={getattr(g,'topLevel','')}")

grbs.close()
print("\n=== End of GRIB2 messages ===")
