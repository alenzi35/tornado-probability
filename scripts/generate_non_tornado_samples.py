import os
import json
import requests
import pygrib
import numpy as np

# ==============================
# OUTPUT FILE
# ==============================

OUTPUT_FILE = "map/data/rap_non_tornado_samples.json"

# ==============================
# RAP TIMES TO SAMPLE
# ==============================

DATES = [
    ("20250621","16"),
    ("20250702","22"),
    ("20250825","18"),
    ("20251008","15")
]

# ==============================
# DOWNLOAD RAP FILE
# ==============================

def download_rap(date, hour):

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"

    fname = f"rap_{date}_{hour}00.grib2"

    if os.path.exists(fname):
        return fname

    print("Downloading", url)

    r = requests.get(url)

    with open(fname,"wb") as f:
        f.write(r.content)

    return fname


# ==============================
# COMPUTE DERIVED VARIABLES
# ==============================

def compute_lcl(t, td):

    # T and Td in Kelvin
    t_c = t - 273.15
    td_c = td - 273.15

    lcl = (t_c - td_c) * 125

    return lcl


def compute_shear(u10, v10, u500, v500):

    return np.sqrt((u500 - u10)**2 + (v500 - v10)**2)


# ==============================
# PROCESS RAP FILE
# ==============================

def process_grib(grib_file):

    print("Processing", grib_file)

    grbs = pygrib.open(grib_file)

    # ------------------------------
    # Surface variables
    # ------------------------------

    t = grbs.select(
        shortName='2t',
        typeOfLevel='heightAboveGround',
        level=2
    )[0].values

    td = grbs.select(
        shortName='2d',
        typeOfLevel='heightAboveGround',
        level=2
    )[0].values

    u10 = grbs.select(
        shortName='10u',
        typeOfLevel='heightAboveGround',
        level=10
    )[0].values

    v10 = grbs.select(
        shortName='10v',
        typeOfLevel='heightAboveGround',
        level=10
    )[0].values


    # ------------------------------
    # 500mb winds
    # ------------------------------

    u500 = grbs.select(
        shortName='u',
        typeOfLevel='isobaricInhPa',
        level=500
    )[0].values

    v500 = grbs.select(
        shortName='v',
        typeOfLevel='isobaricInhPa',
        level=500
    )[0].values


    # ------------------------------
    # CAPE / CIN (0-90mb layer)
    # ------------------------------

    cape = grbs.select(
        shortName='cape',
        typeOfLevel='pressureFromGroundLayer',
        bottomLevel=0,
        topLevel=9000
    )[0].values

    cin = grbs.select(
        shortName='cin',
        typeOfLevel='pressureFromGroundLayer',
        bottomLevel=0,
        topLevel=9000
    )[0].values


    # ------------------------------
    # SRH
    # ------------------------------

    srh = grbs.select(
        shortName='hlcy',
        typeOfLevel='heightAboveGroundLayer',
        bottomLevel=0,
        topLevel=1000
    )[0].values


    # ------------------------------
    # Lat/lon grid
    # ------------------------------

    lats, lons = grbs.select(shortName='2t')[0].latlons()

    # ------------------------------
    # Derived parameters
    # ------------------------------

    lcl = compute_lcl(t, td)

    shear = compute_shear(u10, v10, u500, v500)


    # ------------------------------
    # Flatten grid
    # ------------------------------

    samples = []

    ny, nx = cape.shape

    for j in range(ny):
        for i in range(nx):

            samples.append({
                "cape": float(cape[j,i]),
                "cin": float(cin[j,i]),
                "srh": float(srh[j,i]),
                "lcl": float(lcl[j,i]),
                "shear": float(shear[j,i]),
                "tornado": 0
            })

    return samples


# ==============================
# MAIN
# ==============================

all_samples = []

for date,hour in DATES:

    grib_file = download_rap(date,hour)

    samples = process_grib(grib_file)

    all_samples.extend(samples)

print("Total non-tornado samples:", len(all_samples))


# ==============================
# SAVE
# ==============================

output = {
    "samples": all_samples
}

os.makedirs("map/data", exist_ok=True)

with open(OUTPUT_FILE,"w") as f:
    json.dump(output,f)

print("Saved to", OUTPUT_FILE)
