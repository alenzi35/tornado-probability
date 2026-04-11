import os
import urllib.request
import pygrib
import numpy as np
import pandas as pd
import requests
import zipfile
import io
import geopandas as gpd

from shapely.geometry import box
from shapely.prepared import prep
from pyproj import Proj

# ================= CONFIG =================
DATA_DIR = "data"
OUTPUT_CSV = "map/data/rap_non_tornado_samples.csv"

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= NON-TORNADO TIMES =================
non_tornado_times = [
    {"date":"20250825","hour":"18"},
]

FCST = "01"

# ================= PICK VAR =================
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

# ================= DOWNLOAD SHAPEFILE =================
def download_shapefile(url, folder):
    resp = requests.get(url)
    resp.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    z.extractall(folder)

    shp_file = [f for f in z.namelist() if f.endswith(".shp")][0]
    return gpd.read_file(f"{folder}/{shp_file}")

# ================= PROCESS =================
all_samples = []

for dt in non_tornado_times:

    DATE = dt["date"]
    HOUR = dt["hour"]

    print(f"\nProcessing RAP for {DATE} {HOUR}z")

    RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
    local_file = f"{DATA_DIR}/rap_{DATE}_{HOUR}z_f{FCST}.grib2"

    if not os.path.isfile(local_file):
        print("Downloading", RAP_URL)
        urllib.request.urlretrieve(RAP_URL, local_file)

    grbs = pygrib.open(local_file)

    # ================= VARIABLES =================
    grbs.seek(0)
    cape_msg = pick_var(grbs, "cape", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    cin_msg = pick_var(grbs, "cin", "pressureFromGroundLayer", 0, 9000)

    grbs.seek(0)
    hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

    grbs.seek(0)
    t2m_msg = pick_var(grbs, "2t", "heightAboveGround", level=2)

    grbs.seek(0)
    d2m_msg = pick_var(grbs, "2d", "heightAboveGround", level=2)

    grbs.seek(0)
    u10_msg = pick_var(grbs, "10u", "heightAboveGround", level=10)

    grbs.seek(0)
    v10_msg = pick_var(grbs, "10v", "heightAboveGround", level=10)

    grbs.seek(0)
    u500_msg = pick_var(grbs, "u", "isobaricInhPa", level=500)

    grbs.seek(0)
    v500_msg = pick_var(grbs, "v", "isobaricInhPa", level=500)

    # ================= ARRAYS =================
    cape = np.nan_to_num(cape_msg.values)
    cin = np.nan_to_num(cin_msg.values)
    hlcy = np.nan_to_num(hlcy_msg.values)

    t2m = np.nan_to_num(t2m_msg.values)
    d2m = np.nan_to_num(d2m_msg.values)

    u10 = np.nan_to_num(u10_msg.values)
    v10 = np.nan_to_num(v10_msg.values)

    u500 = np.nan_to_num(u500_msg.values)
    v500 = np.nan_to_num(v500_msg.values)

    lcl = (t2m - d2m) * 125
    shear = np.sqrt((u500 - u10)**2 + (v500 - v10)**2)

    # ================= GRID / PROJECTION =================
    lats, lons = cape_msg.latlons()
    params = cape_msg.projparams

    proj_lcc = Proj(
        proj="lcc",
        lat_1=params["lat_1"],
        lat_2=params["lat_2"],
        lat_0=params["lat_0"],
        lon_0=params["lon_0"],
        a=params.get("a", 6371229),
        b=params.get("b", 6371229)
    )

    x_vals, y_vals = proj_lcc(lons, lats)

    # ================= CONUS POLYGON =================
    print("Downloading CONUS shapefile...")

    states_gdf = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")
    lower48 = states_gdf[~states_gdf["STUSPS"].isin(["AK","HI","PR"])]
    lower48_lcc = lower48.to_crs(proj_lcc.srs)

    conus_poly = lower48_lcc.unary_union
    prepared_conus = prep(conus_poly)

    # ================= FILTER TO CONUS =================
    rows, cols = cape.shape
    kept = 0

    for i in range(rows):
        for j in range(cols):

            x = x_vals[i,j]
            y = y_vals[i,j]

            dx = x_vals[i,j+1]-x if j<cols-1 else x-x_vals[i,j-1]
            dy = y_vals[i+1,j]-y if i<rows-1 else y-y_vals[i-1,j]

            dx, dy = abs(dx), abs(dy)

            cell_box = box(x, y, x+dx, y+dy)

            if not prepared_conus.intersects(cell_box):
                continue

            all_samples.append({
                "date": DATE,
                "hour": HOUR,
                "i": i,
                "j": j,
                "cape": cape[i,j],
                "cin": cin[i,j],
                "hlcy": hlcy[i,j],
                "t2m": t2m[i,j],
                "d2m": d2m[i,j],
                "lcl": lcl[i,j],
                "u10": u10[i,j],
                "v10": v10[i,j],
                "u500": u500[i,j],
                "v500": v500[i,j],
                "shear": shear[i,j],
                "tornado": 0
            })

            kept += 1

    grbs.close()

    print(f"Kept {kept} CONUS cells for {DATE} {HOUR}z")

# ================= SAVE =================
df = pd.DataFrame(all_samples)
df.to_csv(OUTPUT_CSV, index=False)

print(f"\nSaved non-tornado samples to {OUTPUT_CSV}")
print("Total samples:", len(df))
print("DONE.")
