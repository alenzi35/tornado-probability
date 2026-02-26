import os
import urllib.request
import pygrib
import numpy as np
import json
import datetime
import requests
import zipfile
import io

import geopandas as gpd
from shapely.geometry import box
from shapely.prepared import prep
from pyproj import Proj

# ================= CONFIG =================
DATA_DIR = "data"
GRIB_PATH = "data/rap.grib2"
OUTPUT_JSON = "map/data/tornado_prob_lcc.json"

# Standardized LR coefficients from training
COEFFS = {
    "CAPE": 0.92968438,
    "CIN": -0.17418338,
    "HLCY": 0.86443485
}

# === MANUAL INTERCEPT FOR TRIAL-AND-ERROR ===
INTERCEPT_MANUAL = -6.0  # change this to adjust mean probability

# US Census lower 48 states 5m shapefile
CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)

# ================= HELPER FUNCTIONS =================

def get_snapshots():
    return [
        ("20250413", "14"),
        ("20250724", "17"),
        ("20250802", "20"),
        ("20251211", "23")
    ]

def url_exists(url):
    r = requests.head(url)
    return r.status_code == 200

def download_shapefile(url, folder):
    resp = requests.get(url)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    z.extractall(folder)
    shp_file = [f for f in z.namelist() if f.endswith(".shp")][0]
    return gpd.read_file(f"{folder}/{shp_file}")

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel - bottom) < 1 and abs(g.topLevel - top) < 1):
                continue
        return g
    raise RuntimeError(f"{shortname} not found")

# ================= PROCESS SNAPSHOT =================

def process_snapshot(date, hour, fcst="01"):
    print(f"\nProcessing snapshot: {date} {hour} UTC, F{fcst}")

    rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awip32f{fcst}.grib2"
    print("RAP URL:", rap_url)

    if not url_exists(rap_url):
        print("RAP file not ready. Skipping.")
        return None

    urllib.request.urlretrieve(rap_url, GRIB_PATH)
    print("Downloaded RAP GRIB2")

    grbs = pygrib.open(GRIB_PATH)
    grbs.seek(0)
    cape_msg = pick_var(grbs, "cape", "surface")
    grbs.seek(0)
    cin_msg = pick_var(grbs, "cin", "surface")
    grbs.seek(0)
    hlcy_msg = pick_var(grbs, "hlcy", "heightAboveGroundLayer", 0, 1000)

    cape = np.nan_to_num(cape_msg.values)
    cin = np.nan_to_num(cin_msg.values)
    hlcy = np.nan_to_num(hlcy_msg.values)

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

    # ================= USE MANUAL INTERCEPT =================
    intercept = INTERCEPT_MANUAL
    print("Using manual intercept:", intercept)

    # ================= CALC PROB =================
    linear = intercept + COEFFS["CAPE"]*cape + COEFFS["CIN"]*cin + COEFFS["HLCY"]*hlcy
    prob = 1 / (1 + np.exp(-linear))
    print("Snapshot mean probability (decimal):", np.mean(prob))

    # ================= DOWNLOAD CONUS SHAPE =================
    states_gdf = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")
    lower48 = states_gdf[~states_gdf["STUSPS"].isin(["AK","HI","PR"])]
    lower48_lcc = lower48.to_crs(proj_lcc.srs)
    conus_poly = lower48_lcc.unary_union
    prepared_conus = prep(conus_poly)

    # ================= FILTER CELLS =================
    features = []
    rows, cols = prob.shape
    for i in range(rows):
        for j in range(cols):
            x = x_vals[i,j]
            y = y_vals[i,j]
            dx = x_vals[i,j+1] - x if j < cols-1 else x - x_vals[i,j-1]
            dy = y_vals[i+1,j] - y if i < rows-1 else y - y_vals[i-1,j]
            dx, dy = abs(dx), abs(dy)
            cell_box = box(x, y, x+dx, y+dy)
            if prepared_conus.intersects(cell_box):
                features.append({
                    "x": float(x),
                    "y": float(y),
                    "dx": float(dx),
                    "dy": float(dy),
                    "cape": float(cape[i,j]),
                    "cin": float(cin[i,j]),
                    "hlcy": float(hlcy[i,j]),
                    "prob": float(prob[i,j])
                })

    valid_start = f"{int(hour):02d}:00"
    valid_end = f"{(int(hour)+1)%24:02d}:00"

    snapshot_output = {
        "run_date": date,
        "run_hour": hour,
        "forecast": f"F{fcst}",
        "valid": f"{valid_start}-{valid_end} UTC",
        "generated": datetime.datetime.utcnow().isoformat()+"Z",
        "projection": params,
        "features": features
    }

    return snapshot_output

# ================= MAIN =================

def main():
    snapshots_to_process = get_snapshots()
    all_snapshots = []

    for date, hour in snapshots_to_process:
        snap = process_snapshot(date, hour)
        if snap:
            all_snapshots.append(snap)

    # ================= SAVE JSON =================
    output = {
        "snapshots": all_snapshots,
        "generated": datetime.datetime.utcnow().isoformat()+"Z"
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f)

    print("\nSaved tornado probability map to:", OUTPUT_JSON)

    # ================= COMBINED MEAN PROB =================
    all_probs = []
    for snap in all_snapshots:
        for cell in snap["features"]:
            all_probs.append(cell["prob"])
    all_probs = np.array(all_probs)
    combined_mean = np.mean(all_probs)
    print("\nCombined mean probability across all snapshots (decimal):", combined_mean)
    print("Combined mean probability across all snapshots (%):", combined_mean*100)

    print("DONE.")

if __name__ == "__main__":
    main()
