import os
import json
import pandas as pd
import numpy as np
import datetime
import requests
import pygrib

# ================= FILE PATHS =================

TORNADO_CSV = "data/tornado_events.csv"
OUTPUT_JSON = "map/data/rap_unified_dataset.json"

CACHE_DIR = "data/rap_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# ================= RAP DOWNLOAD =================

def download_rap(dt):

    date = dt.strftime("%Y%m%d")
    hour = dt.strftime("%H")

    filename = f"rap_{date}_{hour}.grib2"
    path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(path):
        return path

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awip32f00.grib2"

    print("Downloading:", url)

    r = requests.get(url)

    if r.status_code != 200:
        raise RuntimeError("RAP file unavailable:", url)

    with open(path, "wb") as f:
        f.write(r.content)

    return path


# ================= VARIABLE PICKER =================

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None, level=None):

    for g in grbs:

        if g.shortName != shortname:
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if level is not None and g.level != level:
            continue

        if bottom is not None and hasattr(g,"bottomLevel"):
            if abs(g.bottomLevel-bottom) > 1:
                continue

        if top is not None and hasattr(g,"topLevel"):
            if abs(g.topLevel-top) > 1:
                continue

        return g

    raise RuntimeError(f"{shortname} not found")


# ================= SPATIAL INTERPOLATION =================

def interp_point(values,lats,lons,lat,lon):

    dist = (lats-lat)**2 + (lons-lon)**2
    i,j = np.unravel_index(np.argmin(dist),dist.shape)

    return values[i,j]


# ================= ENVIRONMENT EXTRACTION =================

def extract_env(grib_path,lat,lon):

    grbs = pygrib.open(grib_path)

    cape = pick_var(grbs,"cape","pressureFromGroundLayer",0,9000)
    cin  = pick_var(grbs,"cin","pressureFromGroundLayer",0,9000)
    srh  = pick_var(grbs,"hlcy","heightAboveGroundLayer",0,1000)

    t2   = pick_var(grbs,"2t","heightAboveGround",level=2)
    td2  = pick_var(grbs,"2d","heightAboveGround",level=2)

    u10  = pick_var(grbs,"10u","heightAboveGround",level=10)
    v10  = pick_var(grbs,"10v","heightAboveGround",level=10)

    u500 = pick_var(grbs,"u","isobaricInhPa",level=500)
    v500 = pick_var(grbs,"v","isobaricInhPa",level=500)

    lats,lons = cape.latlons()

    env = {}

    env["cape"] = interp_point(cape.values,lats,lons,lat,lon)
    env["cin"]  = interp_point(cin.values,lats,lons,lat,lon)
    env["hlcy"] = interp_point(srh.values,lats,lons,lat,lon)

    T  = interp_point(t2.values,lats,lons,lat,lon) - 273.15
    Td = interp_point(td2.values,lats,lons,lat,lon) - 273.15

    env["lcl"] = (T - Td) * 125

    u10v = interp_point(u10.values,lats,lons,lat,lon)
    v10v = interp_point(v10.values,lats,lons,lat,lon)

    u500v = interp_point(u500.values,lats,lons,lat,lon)
    v500v = interp_point(v500.values,lats,lons,lat,lon)

    env["shear"] = np.sqrt((u500v-u10v)**2 + (v500v-v10v)**2)

    return env


# ================= TIME INTERPOLATION =================

def time_interp(e0,e1,w):

    out = {}

    for k in e0:
        out[k] = e0[k]*(1-w) + e1[k]*w

    return out


# ================= LOAD CSV =================

print("Loading tornado events...")

df = pd.read_csv(TORNADO_CSV)

samples = []


# ================= PROCESS EVENTS =================

for _,row in df.iterrows():

    date_str = row["Date"]
    valid_str = row["Valid time"]

    lat = row["Latitude"]
    lon = row["Longitude"]

    valid_dt = datetime.datetime.strptime(
        date_str+" "+valid_str,
        "%b %d %Y %H:%M UTC"
    )

    lead_dt = valid_dt - datetime.timedelta(hours=1)

    t0 = lead_dt.replace(minute=0)
    t1 = t0 + datetime.timedelta(hours=1)

    w = (lead_dt - t0).seconds / 3600

    print("Processing:", lead_dt, lat, lon)

    g0 = download_rap(t0)
    g1 = download_rap(t1)

    env0 = extract_env(g0,lat,lon)
    env1 = extract_env(g1,lat,lon)

    env = time_interp(env0,env1,w)

    samples.append({
        "cape": float(env["cape"]),
        "cin": float(env["cin"]),
        "hlcy": float(env["hlcy"]),
        "lcl": float(env["lcl"]),
        "shear": float(env["shear"]),
        "tornado": 1
    })


# ================= SAVE DATASET =================

output = {
    "total_samples": len(samples),
    "tornado_count": len(samples),
    "non_tornado_count": 0,
    "samples": samples
}

with open(OUTPUT_JSON,"w") as f:
    json.dump(output,f)

print("\nUnified dataset saved:", OUTPUT_JSON)
print("Total samples:", output["total_samples"])
print("DONE.")
