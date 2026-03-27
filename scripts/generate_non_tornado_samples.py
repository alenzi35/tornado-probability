import os
import requests
import pygrib
import pandas as pd

OUTPUT = "data/non_tornado_samples.csv"

dates = [
    ("20250621", "16"),
    ("20250702", "22"),
    ("20250825", "18"),
    ("20251008", "15"),
]

os.makedirs("data", exist_ok=True)

rows = []

for date, hour in dates:

    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.awp130bgrbf00.grib2"
    filename = f"rap_{date}_{hour}00.grib2"

    print("Downloading:", url)

    if not os.path.exists(filename):
        r = requests.get(url)
        with open(filename, "wb") as f:
            f.write(r.content)

    print("Opening GRIB:", filename)

    grbs = pygrib.open(filename)

    try:
        cape = grbs.select(shortName="cape")[0]
        cin = grbs.select(shortName="cin")[0]
        t2m = grbs.select(shortName="2t")[0]
        u10 = grbs.select(shortName="10u")[0]
        v10 = grbs.select(shortName="10v")[0]
    except Exception as e:
        print("Variable missing:", e)
        continue

    cape_vals = cape.values
    cin_vals = cin.values
    t_vals = t2m.values
    u_vals = u10.values
    v_vals = v10.values

    lats, lons = cape.latlons()

    ny, nx = cape_vals.shape

    for y in range(ny):
        for x in range(nx):

            rows.append({
                "lat": float(lats[y,x]),
                "lon": float(lons[y,x]),
                "cape": float(cape_vals[y,x]),
                "cin": float(cin_vals[y,x]),
                "t2m": float(t_vals[y,x]),
                "u10": float(u_vals[y,x]),
                "v10": float(v_vals[y,x]),
                "tornado": 0
            })

df = pd.DataFrame(rows)

df.to_csv(OUTPUT, index=False)

print("Saved samples:", len(df))
