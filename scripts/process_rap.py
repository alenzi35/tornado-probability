import os, pygrib, json, numpy as np
import pyproj

DATE = "20260128"
HOUR = "19"
FCST = "02"
RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob.json"

INTERCEPT = -1.5686
COEFFS = {"CAPE":2.88592370e-03,"CIN":2.38728498e-05,"HLCY":8.85192696e-03}

os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# Download GRIB
if not os.path.exists(GRIB_PATH):
    import urllib.request
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(RAP_URL, GRIB_PATH)

grbs = pygrib.open(GRIB_PATH)
def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower(): continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel: continue
        if bottom is not None and top is not None:
            if not hasattr(g,"bottomLevel") or not hasattr(g,"topLevel"): continue
            if not (abs(g.bottomLevel-bottom)<1 and abs(g.topLevel-top)<1): continue
        return g
    raise RuntimeError(f"{shortname} not found")

cape = pick_var(grbs,"cape","surface").values
cin  = pick_var(grbs,"cin","surface").values
hlcy = pick_var(grbs,"hlcy","heightAboveGroundLayer",0,1000).values
rows, cols = cape.shape

lats, lons = pick_var(grbs,"cape","surface").latlons()

# Convert 13.545 km to degrees
def km_to_deg(lat, km):
    deg_lat = km / 111.32  # ~1 deg lat = 111.32 km
    deg_lon = km / (111.32 * np.cos(np.radians(lat)))
    return deg_lat, deg_lon

features = []
for i in range(rows):
    for j in range(cols):
        lat = lats[i,j]
        lon = lons[i,j]
        linear = INTERCEPT + COEFFS["CAPE"]*cape[i,j] + COEFFS["CIN"]*cin[i,j] + COEFFS["HLCY"]*hlcy[i,j]
        prob = 1 / (1 + np.exp(-linear))
        dlat, dlon = km_to_deg(lat, 13.545/2)  # half-width in degrees
        features.append({
            "lat_min": float(lat - dlat),
            "lat_max": float(lat + dlat),
            "lon_min": float(lon - dlon),
            "lon_max": float(lon + dlon),
            "prob": float(prob)
        })

with open(OUTPUT_JSON,"w") as f:
    json.dump(features,f,indent=2)

print("✅ Tornado probability JSON written with exact rectangle lat/lon")
