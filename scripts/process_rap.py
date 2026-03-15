import urllib.request
import pygrib
import numpy as np
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------

RUN_DATE = "20260314"
RUN_HOUR = "22"
FORECAST = "01"

URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{RUN_DATE}/rap.t{RUN_HOUR}z.awip32f{FORECAST}.grib2"
FILE = "rap.grib2"

print(f"Target: {RUN_DATE} {RUN_HOUR} F{FORECAST}")
print("URL:", URL)

# -----------------------------
# DOWNLOAD
# -----------------------------

urllib.request.urlretrieve(URL, FILE)
print("Downloaded RAP GRIB2")

# -----------------------------
# VARIABLE PICKER
# -----------------------------

def pick_var(grbs, shortName, typeOfLevel, bottomLevel, topLevel):
    for g in grbs:
        if (
            g.shortName.lower() == shortName.lower()
            and g.typeOfLevel == typeOfLevel
            and getattr(g, "bottomLevel", None) == bottomLevel
            and getattr(g, "topLevel", None) == topLevel
        ):
            return g
    raise RuntimeError(
        f"Variable not found: shortName={shortName}, typeOfLevel={typeOfLevel}, bottomLevel={bottomLevel}, topLevel={topLevel}"
    )

# -----------------------------
# OPEN GRIB
# -----------------------------

grbs = pygrib.open(FILE)

# -----------------------------
# EXTRACT VARIABLES
# -----------------------------

cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 18000)
cin_msg = pick_var(grbs, "cin", "pressureFromGroundLayer", 0, 18000)
hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

t2_msg = pick_var(grbs, "2t", "heightAboveGround", 2, 2)
td2_msg = pick_var(grbs, "2d", "heightAboveGround", 2, 2)

u10_msg = pick_var(grbs, "10u", "heightAboveGround", 10, 10)
v10_msg = pick_var(grbs, "10v", "heightAboveGround", 10, 10)

u500_msg = pick_var(grbs, "u", "isobaricInhPa", 500, 500)
v500_msg = pick_var(grbs, "v", "isobaricInhPa", 500, 500)

# -----------------------------
# LOAD DATA ARRAYS
# -----------------------------

cape = cape_msg.values
cin = cin_msg.values
srh = hlcy_msg.values

t2 = t2_msg.values
td2 = td2_msg.values

u10 = u10_msg.values
v10 = v10_msg.values

u500 = u500_msg.values
v500 = v500_msg.values

lats, lons = cape_msg.latlons()

# -----------------------------
# BASIC DERIVED FIELDS
# -----------------------------

# convert K -> C
t2c = t2 - 273.15
td2c = td2 - 273.15

# wind speed
wind10 = np.sqrt(u10**2 + v10**2)
wind500 = np.sqrt(u500**2 + v500**2)

# simple shear magnitude
shear = np.sqrt((u500 - u10)**2 + (v500 - v10)**2)

# -----------------------------
# OUTPUT STRUCTURE
# -----------------------------

data = {
    "cape": cape,
    "cin": cin,
    "srh": srh,
    "t2c": t2c,
    "td2c": td2c,
    "u10": u10,
    "v10": v10,
    "u500": u500,
    "v500": v500,
    "wind10": wind10,
    "wind500": wind500,
    "shear": shear,
    "lat": lats,
    "lon": lons,
}

print("Extraction complete")
print("Grid shape:", cape.shape)
