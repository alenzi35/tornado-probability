import urllib.request
import pygrib
import numpy as np

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
# OPEN GRIB
# -----------------------------

grbs = pygrib.open(FILE)

# -----------------------------
# VARIABLE PICKER
# -----------------------------

def pick(shortName, typeOfLevel, level):
    msgs = grbs.select(shortName=shortName, typeOfLevel=typeOfLevel, level=level)
    if len(msgs) == 0:
        raise RuntimeError(
            f"Variable not found: shortName={shortName}, typeOfLevel={typeOfLevel}, level={level}"
        )
    return msgs[0]

# -----------------------------
# EXTRACT VARIABLES
# -----------------------------

cape_msg = pick("cape", "pressureFromGroundLayer", 18000)
cin_msg  = pick("cin",  "pressureFromGroundLayer", 18000)

hlcy_msg = pick("hlcy", "heightAboveGroundLayer", 1000)

t2_msg  = pick("2t",  "heightAboveGround", 2)
td2_msg = pick("2d",  "heightAboveGround", 2)

u10_msg = pick("10u", "heightAboveGround", 10)
v10_msg = pick("10v", "heightAboveGround", 10)

u500_msg = pick("u", "isobaricInhPa", 500)
v500_msg = pick("v", "isobaricInhPa", 500)

# -----------------------------
# LOAD ARRAYS
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
# DERIVED FIELDS
# -----------------------------

t2c = t2 - 273.15
td2c = td2 - 273.15

wind10 = np.sqrt(u10**2 + v10**2)
wind500 = np.sqrt(u500**2 + v500**2)

shear = np.sqrt((u500-u10)**2 + (v500-v10)**2)

print("Extraction complete")
print("Grid shape:", cape.shape)
