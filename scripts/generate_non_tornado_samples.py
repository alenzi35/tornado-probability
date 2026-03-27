import pygrib
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path

OUTPUT = "map/data/rap_non_tornado_samples.csv"

RUN_TIMES = [
    "20250621_1600",
    "20250702_2200",
    "20250825_1800",
    "20251008_1500"
]

def download_rap(run):
    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{run[:8]}/rap.t{run[9:11]}z.awp130bgrbf00.grib2"
    filename = f"rap_{run}.grib2"

    if Path(filename).exists():
        return filename

    print("Downloading", url)

    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


def compute_lcl(T, Td):
    return (T - Td) * 125


def compute_shear(u10, v10, u500, v500):
    return np.sqrt((u500 - u10)**2 + (v500 - v10)**2)


rows = []

for run in RUN_TIMES:

    file = download_rap(run)

    print("Processing", file)

    grbs = pygrib.open(file)

    cape = grbs.select(shortName='cape')[0].values
    cin = grbs.select(shortName='cin')[0].values
    t = grbs.select(shortName='t', level=2)[0].values
    td = grbs.select(shortName='dpt', level=2)[0].values

    u10 = grbs.select(shortName='10u')[0].values
    v10 = grbs.select(shortName='10v')[0].values

    u500 = grbs.select(shortName='u', level=500)[0].values
    v500 = grbs.select(shortName='v', level=500)[0].values

    lats, lons = grbs.select(shortName='cape')[0].latlons()

    LCL = compute_lcl(t, td)
    SHEAR = compute_shear(u10, v10, u500, v500)

    for i in range(cape.shape[0]):
        for j in range(cape.shape[1]):

            rows.append({
                "latitude": lats[i,j],
                "longitude": lons[i,j],
                "cape": cape[i,j],
                "cin": cin[i,j],
                "srh": 0,
                "lcl": LCL[i,j],
                "shear": SHEAR[i,j],
                "tornado": 0
            })

df = pd.DataFrame(rows)

df.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)
print("Rows:", len(df))
