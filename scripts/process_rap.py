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
OUTPUT_PNG = "map/rap_prob.png"

# Logistic regression
INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}

os.makedirs("data", exist_ok=True)
os.makedirs("map", exist_ok=True)

# ---------------- DOWNLOAD ----------------
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)

# ---------------- OPEN GRIB ----------------
grbs = pygrib.open(GRIB_PATH)

cape = grbs.select(shortName="cape", typeOfLevel="surface")[0].values
cin  = grbs.select(shortName="cin",  typeOfLevel="surface")[0].values
hlcy = grbs.select(shortName="hlcy", typeOfLevel="heightAboveGroundLayer")[0].values

lats, lons = grbs.select(shortName="cape")[0].latlons()

# ---------------- PROBABILITY ----------------
linear = INTERCEPT + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
prob = 1 / (1 + np.exp(-linear))

# ---------------- LCC PROJECTION ----------------
rap_lcc = ccrs.LambertConformal(
    central_longitude=-97.5,
    central_latitude=38.5,
    standard_parallels=(38.5, 38.5)
)

fig = plt.figure(figsize=(14, 9))
ax = plt.axes(projection=rap_lcc)

ax.set_extent([-125, -66, 24, 50], crs=ccrs.PlateCarree())

mesh = ax.pcolormesh(
    lons, lats, prob,
    transform=ccrs.PlateCarree(),
    shading="nearest",   # IMPORTANT: preserves touching cells
    cmap="hot"
)

plt.colorbar(mesh, orientation="vertical", pad=0.02, label="Tornado Probability")
plt.title("RAP Tornado Probability (Native Grid)")

plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
plt.close()

print("✅ Saved:", OUTPUT_PNG)
