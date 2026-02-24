import os
import urllib.request
import pygrib
import numpy as np
import json
import subprocess

DATA_DIR = "data"
GRIB_PATH = f"{DATA_DIR}/rap.grib2"
GRID_JSON = f"{DATA_DIR}/rap_grid.json"
DATASET_JSON = f"{DATA_DIR}/dataset.json"

os.makedirs(DATA_DIR, exist_ok=True)

# 4 historical RAP analysis snapshots
SNAPSHOTS = [
    ("20250724", "14"),
    ("20250915", "17"),
    ("20250921", "20"),
    ("20251230", "23"),
]

def download_rap(date, hour):
    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awip32f00.grib2"
    print("Downloading:", url)
    urllib.request.urlretrieve(url, GRIB_PATH)

def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue
        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue
        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if not (abs(g.bottomLevel-bottom)<1 and abs(g.topLevel-top)<1):
                continue
        return g
    raise RuntimeError(f"{shortname} not found")

def extract_grid():
    grbs = pygrib.open(GRIB_PATH)

    grbs.seek(0)
    cape = pick_var(grbs,"cape","pressureFromGroundLayer",0,9000).values

    grbs.seek(0)
    cin = pick_var(grbs,"cin","pressureFromGroundLayer",0,9000).values

    grbs.seek(0)
    hlcy = pick_var(grbs,"hlcy","heightAboveGroundLayer",0,1000).values

    cape = np.nan_to_num(cape)
    cin = np.nan_to_num(cin)
    hlcy = np.nan_to_num(hlcy)

    rows, cols = cape.shape

    samples = []

    for i in range(rows):
        for j in range(cols):

            samples.append({
                "CAPE": float(cape[i,j]),
                "CIN": float(cin[i,j]),
                "HLCY": float(hlcy[i,j]),
                "tornado": 0
            })

    print("Extracted", len(samples), "non-tornado samples")

    return samples


def load_tornado_samples():

    path = "data/tornado_samples.json"

    if not os.path.exists(path):
        print("No tornado samples found yet")
        return []

    with open(path) as f:
        data = json.load(f)

    print("Loaded", len(data), "tornado samples")

    return data


def main():

    dataset = []

    for date, hour in SNAPSHOTS:

        print("\nProcessing snapshot:", date, hour)

        download_rap(date, hour)

        samples = extract_grid()

        dataset.extend(samples)

    tornado_samples = load_tornado_samples()

    dataset.extend(tornado_samples)

    print("\nFinal dataset size:", len(dataset))

    with open(DATASET_JSON,"w") as f:
        json.dump(dataset,f)

    print("Saved dataset:", DATASET_JSON)


if __name__ == "__main__":
    main()
