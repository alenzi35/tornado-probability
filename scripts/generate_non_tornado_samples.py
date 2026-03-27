import os
import json
import urllib.request
import pygrib
import numpy as np

# ==============================
# OUTPUT
# ==============================

OUTPUT_FILE = "map/data/rap_non_tornado_samples.json"

# ==============================
# RAP ANALYSIS TIMES
# ==============================

DATES = [
    ("20250621","16"),
    ("20250702","22"),
    ("20250825","18"),
    ("20251008","15")
]

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ==============================
# VARIABLE PICKER (same as process_rap)
# ==============================

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None, level=None):

    for g in grbs:

        if g.shortName.lower() != shortname.lower():
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None and hasattr(g, "level"):
            if abs(g.level - level) > 0.1:
                continue

        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue

        return g

    raise RuntimeError(f"{shortname} not found")

# ==============================
# DOWNLOAD RAP
# ==============================

def download_rap(date, hour):

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"

    fname = f"{DATA_DIR}/rap_{date}_{hour}00.grib2"

    if os.path.exists(fname):
        return fname

    print("Downloading", url)

    urllib.request.urlretrieve(url, fname)

    return fname


# ==============================
# DERIVED VARIABLES
# ==============================

def compute_lcl(t, td):

    t_c = t - 273.15
    td_c = td - 273.15

    return (t_c - td_c) * 125


def compute_shear(u10, v10, u500, v500):

    return np.sqrt((u500-u10)**2 + (v500-v10)**2)


# ==============================
# PROCESS GRIB
# ==============================

def process_grib(grib_file):

    print("Processing", grib_file)

    grbs = pygrib.open(grib_file)

    # CAPE
    grbs.seek(0)
    cape_msg = pick_var(grbs,"cape","pressureFromGroundLayer",0,9000)

    # CIN
    grbs.seek(0)
    cin_msg = pick_var(grbs,"cin","pressureFromGroundLayer",0,9000)

    # SRH
    grbs.seek(0)
    hlcy_msg = pick_var(grbs,"hlcy","heightAboveGroundLayer",0,1000)

    cape = np.nan_to_num(cape_msg.values)
    cin = np.nan_to_num(cin_msg.values)
    srh = np.nan_to_num(hlcy_msg.values)

    # 2m T
    grbs.seek(0)
    t_msg = pick_var(grbs,"2t","heightAboveGround",level=2)

    # 2m Td
    grbs.seek(0)
    td_msg = pick_var(grbs,"2d","heightAboveGround",level=2)

    # 10m winds
    grbs.seek(0)
    u10_msg = pick_var(grbs,"10u","heightAboveGround",level=10)

    grbs.seek(0)
    v10_msg = pick_var(grbs,"10v","heightAboveGround",level=10)

    # 500mb winds
    grbs.seek(0)
    u500_msg = pick_var(grbs,"u","isobaricInhPa",level=500)

    grbs.seek(0)
    v500_msg = pick_var(grbs,"v","isobaricInhPa",level=500)

    t = np.nan_to_num(t_msg.values)
    td = np.nan_to_num(td_msg.values)

    u10 = np.nan_to_num(u10_msg.values)
    v10 = np.nan_to_num(v10_msg.values)

    u500 = np.nan_to_num(u500_msg.values)
    v500 = np.nan_to_num(v500_msg.values)

    # derived
    lcl = compute_lcl(t,td)
    shear = compute_shear(u10,v10,u500,v500)

    # flatten grid
    samples = []

    ny,nx = cape.shape

    for j in range(ny):
        for i in range(nx):

            samples.append({

                "cape":float(cape[j,i]),
                "cin":float(cin[j,i]),
                "srh":float(srh[j,i]),
                "lcl":float(lcl[j,i]),
                "shear":float(shear[j,i]),

                "tornado":0

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

print("Total samples:",len(all_samples))

output = {"samples":all_samples}

with open(OUTPUT_FILE,"w") as f:
    json.dump(output,f)

print("Saved:",OUTPUT_FILE)
