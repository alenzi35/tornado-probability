import os
import urllib.request
import numpy as np
import rasterio
import matplotlib.pyplot as plt

# ================= CONFIG =================

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
PATH = os.path.join(DATA_DIR, "nbm.tif")

URL = "https://noaa-nbm-pds.s3.amazonaws.com/blendv5.0/conus/2026/06/06/1500/spctor4hr/blendv5.0_conus_spctor4hr_2026-06-06T15%3A00_2026-06-06T19%3A00.tif"

os.makedirs(DATA_DIR, exist_ok=True)

# ================= DOWNLOAD IF NEEDED =================

if not os.path.exists(PATH):
    print("Downloading NBM file...")
    urllib.request.urlretrieve(URL, PATH)
    print("Download complete.")
else:
    print("NBM file already exists.")

# ================= OPEN RASTER =================

with rasterio.open(PATH) as src:

    print("\n==============================")
    print("NBM FILE INSPECTION")
    print("==============================\n")

    print("Driver:", src.driver)
    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Dtypes:", src.dtypes)

    print("\n------------------------------\n")

    best_band = None
    best_range = -1

    # ================= BAND ANALYSIS =================

    for i in range(1, src.count + 1):

        band = src.read(i).astype(float)
        band_clean = band[~np.isnan(band)]

        if len(band_clean) == 0:
            continue

        mn = np.nanmin(band_clean)
        mx = np.nanmax(band_clean)
        mean = np.nanmean(band_clean)
        rng = mx - mn

        print(f"Band {i}")
        print("  min:", mn)
        print("  max:", mx)
        print("  mean:", mean)
        print("  range:", rng)
        print("------------------------------")

        if rng > best_range:
            best_range = rng
            best_band = i

    print("\nSelected band:", best_band)

    data = src.read(best_band).astype(float)

# ================= CLEAN FLATTEN =================

flat = data.flatten()
flat = flat[~np.isnan(flat)]

print("\n==============================")
print("GLOBAL STATS")
print("==============================")

print("Min:", np.min(flat))
print("Max:", np.max(flat))
print("Mean:", np.mean(flat))
print("Median:", np.median(flat))
print("Unique sample:", len(np.unique(flat[:200000])))

# ================= HISTOGRAM =================

plt.figure()
plt.hist(flat, bins=60)
plt.title("NBM Value Distribution")
plt.xlabel("Value")
plt.ylabel("Frequency")
plt.show()

# ================= SPATIAL VIEW =================

plt.figure()
plt.imshow(data, cmap="turbo")
plt.title("NBM Selected Band Field")
plt.colorbar()
plt.show()
