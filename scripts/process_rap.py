import os
import urllib.request
import pygrib
import numpy as np
from PIL import Image
import json
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


# ---------------- CONFIG ----------------
DATE = "20260128"
HOUR = "19"
FCST = "02"

RAP_URL = f"https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"
GRIB_PATH = "data/rap.grib2"

OUTPUT_PNG  = "map/data/tornado_prob.png"
OUTPUT_JSON = "map/data/tornado_prob_pixels.json"

INTERCEPT = -1.5686
COEFFS = {
    "CAPE": 2.88592370e-03,
    "CIN":  2.38728498e-05,
    "HLCY": 8.85192696e-03
}
# ----------------------------------------


os.makedirs("data", exist_ok=True)
os.makedirs("map/data", exist_ok=True)


# ---------------- Download RAP ----------------
print("Downloading RAP...")
urllib.request.urlretrieve(RAP_URL, GRIB_PATH)
print("Download complete")


# ---------------- Open GRIB ----------------
grbs = pygrib.open(GRIB_PATH)


def pick_var(grbs, shortname, typeOfLevel=None, bottom=None, top=None):
    for g in grbs:
        if g.shortName.lower() != shortname.lower():
            continue

        if typeOfLevel and g.typeOfLevel != typeOfLevel:
            continue

        if bottom is not None and top is not None:
            if not hasattr(g, "bottomLevel"):
                continue
            if abs(g.bottomLevel-bottom)>1 or abs(g.topLevel-top)>1:
                continue

        return g

    raise RuntimeError(f"{shortname} NOT FOUND")


# ---------------- Extract vars ----------------
grbs.seek(0)
cape = pick_var(grbs,"cape","surface").values

grbs.seek(0)
cin  = pick_var(grbs,"cin","surface").values

grbs.seek(0)
hlcy = pick_var(
    grbs,"hlcy",
    "heightAboveGroundLayer",0,1000
).values


rows, cols = cape.shape


# ---------------- Probability ----------------
linear = (
    INTERCEPT
    + COEFFS["CAPE"]*cape
    + COEFFS["CIN"]*cin
    + COEFFS["HLCY"]*hlcy
)

prob = 1/(1+np.exp(-linear))


# ---------------- Color raster ----------------
img = Image.new("RGB",(cols,rows))

for i in range(rows):
    for j in range(cols):

        p = np.clip(prob[i,j],0,1)

        if p<0.3:
            r = int(255*(p/0.3))
            g = int(255*(p/0.3))
            b = 255

        elif p<0.6:
            r = 255
            g = int(255*(1-(p-0.3)/0.3))
            b = 0

        else:
            r = 255
            g = int(255*(1-(p-0.6)/0.4))
            b = 0

        img.putpixel((j,i),(r,g,b))


img.save(OUTPUT_PNG)


# ---------------- Overlay geography ----------------
print("Adding borders...")

rap_proj = ccrs.LambertConformal(
    central_longitude=-97,
    central_latitude=40,
    standard_parallels=(33,45)
)

fig = plt.figure(figsize=(cols/100,rows/100),dpi=100)
ax = plt.axes(projection=rap_proj)

img2 = plt.imread(OUTPUT_PNG)

ax.imshow(img2,origin="upper",transform=rap_proj)

ax.add_feature(cfeature.STATES,linewidth=0.5)
ax.add_feature(cfeature.COASTLINE,linewidth=0.5)
ax.add_feature(cfeature.BORDERS,linewidth=0.5)

ax.axis("off")

plt.savefig(
    OUTPUT_PNG,
    bbox_inches="tight",
    pad_inches=0,
    dpi=100
)

plt.close()


# ---------------- Pixel JSON ----------------
features=[]

for i in range(rows):
    for j in range(cols):
        features.append({
            "row":i,
            "col":j,
            "prob":float(prob[i,j])
        })


with open(OUTPUT_JSON,"w") as f:
    json.dump(features,f)


print("DONE")
