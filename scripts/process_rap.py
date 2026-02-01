import os
import urllib.request
import pygrib
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_IMG = "map/data/tornado_prob.png"

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ---------------- DOWNLOAD RAP ----------------
print("Downloading RAP GRIB...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("✅ Download complete.")

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel") or not hasattr(g, "topLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        return g
    raise RuntimeError(f"{shortname} NOT FOUND")

# ---------------- EXTRACT VARIABLES ----------------
cape_msg = pick_var(grbs, "cape", typeOfLevel="surface")
cin_msg  = pick_var(grbs, "cin", typeOfLevel="surface")
hlcy_msg = pick_var(grbs, "hlcy", typeOfLevel="heightAboveGroundLayer", bottom=0, top=1000)

cape = cape_msg.values
cin = cin_msg.values
hlcy = hlcy_msg.values
lats, lons = cape_msg.latlons()

# ---------------- COMPUTE PROBABILITY ----------------
INTERCEPT = -1.5686
COEFFS = {"CAPE": 2.88592370e-03, "CIN":  2.38728498e-05, "HLCY": 8.85192696e-03}
linear = INTERCEPT + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- PLOT TO IMAGE ----------------
plt.figure(figsize=(12,8))
ax = plt.axes(projection=ccrs.LambertConformal())
ax.set_extent([-125, -66, 22, 50], crs=ccrs.PlateCarree())

# Use pcolormesh for the RAP grid
mesh = ax.pcolormesh(lons, lats, prob, transform=ccrs.PlateCarree(), cmap='hot')
plt.axis('off')
plt.savefig(OUTPUT_IMG, bbox_inches='tight', dpi=150)
plt.close()
print("✅ Tornado probability image saved:", OUTPUT_IMG)
