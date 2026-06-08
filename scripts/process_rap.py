import rasterio
import numpy as np
import matplotlib.pyplot as plt

PATH = "data/nbm.tif"


print("\n==============================")
print("NBM GEO TIFF FULL INSPECTION")
print("==============================\n")

with rasterio.open(PATH) as src:

    # ---------------- BASIC INFO ----------------
    print("Driver:", src.driver)
    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Dtypes:", src.dtypes)
    print("\n------------------------------\n")

    # ---------------- BAND ANALYSIS ----------------
    best_band = None
    best_range = -1

    for i in range(1, src.count + 1):

        band = src.read(i).astype(float)

        band_clean = band[~np.isnan(band)]

        if len(band_clean) == 0:
            continue

        mn = np.nanmin(band_clean)
        mx = np.nanmax(band_clean)
        mean = np.nanmean(band_clean)
        unique_sample = len(np.unique(band_clean[:10000]))

        rng = mx - mn

        print(f"Band {i}")
        print("  min:", mn)
        print("  max:", mx)
        print("  mean:", mean)
        print("  sample unique count:", unique_sample)
        print("  range:", rng)
        print("------------------------------")

        if rng > best_range:
            best_range = rng
            best_band = i

    print("\nSelected most informative band:", best_band)

    # ---------------- LOAD BEST BAND ----------------
    data = src.read(best_band).astype(float)

# ---------------- GLOBAL STATS ----------------

flat = data.flatten()
flat = flat[~np.isnan(flat)]

print("\n==============================")
print("GLOBAL STATISTICS")
print("==============================")

print("Min:", np.min(flat))
print("Max:", np.max(flat))
print("Mean:", np.mean(flat))
print("Median:", np.median(flat))
print("Unique values (sample):", len(np.unique(flat[:200000])))

# ---------------- TOP VALUES ----------------

print("\nTop hotspots:")
top_idx = np.dstack(np.unravel_index(np.argsort(flat)[-10:], data.shape))[0]
print(top_idx)

# ---------------- HISTOGRAM ----------------

plt.figure()
plt.hist(flat, bins=60)
plt.title("NBM Value Distribution")
plt.xlabel("Value")
plt.ylabel("Frequency")
plt.show()

# ---------------- SPATIAL SNAPSHOT ----------------

plt.figure()
plt.imshow(data, cmap="turbo")
plt.title("NBM Spatial Field (best band)")
plt.colorbar()
plt.show()
