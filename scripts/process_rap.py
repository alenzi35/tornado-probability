import datetime
import requests
import pygrib
import numpy as np

def get_latest_cycle():
    now = datetime.datetime.utcnow()
    cycle = now.hour
    return now.strftime("%Y%m%d"), f"{cycle:02d}"

def download_grib(date, hour):
    url = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{date}/rap.t{hour}z.wrfnatf01.grib2"
    print("URL:", url)

    r = requests.get(url)
    with open("rap.grib2", "wb") as f:
        f.write(r.content)

    print("Downloaded RAP GRIB2")

def pick_var(grbs, keywords):
    for g in grbs:
        name = g.name.lower()
        short = g.shortName.lower()

        for k in keywords:
            if k in name or k in short:
                print("Found:", g.name)
                return g

    raise RuntimeError(f"{keywords} not found")

date, hour = get_latest_cycle()
print("Target:", date, hour, "F01")

download_grib(date, hour)

grbs = pygrib.open("rap.grib2")

cape_msg = pick_var(grbs, ["cape"])
cin_msg = pick_var(grbs, ["convective inhibition", "cin"])
hlcy_msg = pick_var(grbs, ["helicity", "hlcy", "storm relative helicity"])
u_msg = pick_var(grbs, ["u component of wind"])
v_msg = pick_var(grbs, ["v component of wind"])
depr_msg = pick_var(grbs, ["dew point depression", "depr"])

cape = cape_msg.values
cin = cin_msg.values
hlcy = hlcy_msg.values
u = u_msg.values
v = v_msg.values
depr = depr_msg.values

shear = np.sqrt(u**2 + v**2)

prob = (
    0.35 * (cape / 3000) +
    0.25 * (hlcy / 300) +
    0.20 * (shear / 40) +
    0.10 * ((-cin) / 200) +
    0.10 * (depr / 20)
)

prob = np.clip(prob, 0, 1)

print("Computed probability grid")
