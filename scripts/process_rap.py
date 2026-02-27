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

COEFFS = {
    "CAPE": 0.92968438,
    "CIN": -0.17418338,
    "HLCY": 0.86443485
}

# ===== MANUAL INTERCEPT =====
INTERCEPT_MANUAL = -6.0   # <-- adjust manually for calibration

CONUS_SHAPE_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("map/data", exist_ok=True)


# ================= SNAPSHOT CONFIG (GITHUB ACTIONS SAFE) =================

def get_snapshot_from_env():
    """
    Uses GitHub Actions environment variables:
        RAP_DATE=YYYYMMDD
        RAP_HOUR=HH

    If not set, defaults to test case.
    """

    date = os.getenv("RAP_DATE")
    hour = os.getenv("RAP_HOUR")

    if date and hour:
        print(f"Using RAP_DATE={date}, RAP_HOUR={hour}")
        return date, hour

    print("No RAP_DATE/RAP_HOUR provided. Using default test case.")
    return "20250427", "21"


# ================= HELPERS =================

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


# ================= MAIN PROCESS =================

def main():

    date, hour = get_snapshot_from_env()

    print(f"\nProcessing RAP snapshot: {date} {hour} UTC")

    rap_url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awip32f01.grib2"
    print("RAP URL:", rap_url)

    if not url_exists(rap_url):
        print("RAP file not available.")
        return

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

    # ===== Logistic Regression =====
    intercept = INTERCEPT_MANUAL
    print("Using manual intercept:", intercept)

    linear = (
        intercept
        + COEFFS["CAPE"] * cape
        + COEFFS["CIN"] * cin
        + COEFFS["HLCY"] * hlcy
    )

    prob = 1 / (1 + np.exp(-linear))

    print("Snapshot mean probability (decimal):", np.mean(prob))
    print("Snapshot mean probability (%):", np.mean(prob) * 100)

    # ===== CONUS FILTER =====
    states_gdf = download_shapefile(CONUS_SHAPE_URL, "tmp_conus")
    lower48 = states_gdf[~states_gdf["STUSPS"].isin(["AK", "HI", "PR"])]
    lower48_lcc = lower48.to_crs(proj_lcc.srs)
    conus_poly = lower48_lcc.unary_union
    prepared_conus = prep(conus_poly)

    features = []
    rows, cols = prob.shape

    for i in range(rows):
        for j in range(cols):

            x = x_vals[i, j]
            y = y_vals[i, j]

            dx = x_vals[i, j + 1] - x if j < cols - 1 else x - x_vals[i, j - 1]
            dy = y_vals[i + 1, j] - y if i < rows - 1 else y - y_vals[i - 1, j]

            dx, dy = abs(dx), abs(dy)
            cell_box = box(x, y, x + dx, y + dy)

            if prepared_conus.intersects(cell_box):
                features.append({
                    "x": float(x),
                    "y": float(y),
                    "dx": float(dx),
                    "dy": float(dy),
                    "cape": float(cape[i, j]),
                    "cin": float(cin[i, j]),
                    "hlcy": float(hlcy[i, j]),
                    "prob": float(prob[i, j])
                })

    print(f"Kept {len(features)} cells inside CONUS.")

    output = {
        "snapshots": [{
            "run_date": date,
            "run_hour": hour,
            "forecast": "F01",
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "projection": params,
            "features": features
        }],
        "generated": datetime.datetime.utcnow().isoformat() + "Z"
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f)

    print("\nSaved tornado probability map to:", OUTPUT_JSON)

    # ===== Combined Mean (Single Snapshot Here) =====
    all_probs = [cell["prob"] for cell in features]
    combined_mean = np.mean(all_probs)

    print("\nCombined mean probability (decimal):", combined_mean)
    print("Combined mean probability (%):", combined_mean * 100)

    print("DONE.")


if __name__ == "__main__":
    main()
