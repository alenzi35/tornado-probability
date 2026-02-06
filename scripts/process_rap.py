import os
import json
import shutil
import subprocess
import urllib.request
import numpy as np
import pygrib
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

# ---------------- Paths ----------------

DATA_DIR = "data"
MAP_DIR = "map"
TILE_DIR = "map/tiles"

GRIB_FILE = f"{DATA_DIR}/rap.grib2"
RASTER_FILE = f"{MAP_DIR}/output.tif"
TMP_MERCATOR = f"{MAP_DIR}/output_3857.tif"

# Update RAP URL with the current date / forecast hour as needed
RAP_URL = (
    "https://nomads.ncep.noaa.gov/pub/data/nccf/com/rap/prod/"
    "rap.20260206/rap.t00z.awp130pgrbf00.grib2"
)

# ---------------- Setup ----------------

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)

print("Starting RAP processing...")

# ---------------- Download RAP ----------------

if not os.path.exists(GRIB_FILE):
    print("Downloading RAP GRIB...")
    urllib.request.urlretrieve(RAP_URL, GRIB_FILE)
else:
    print("Using cached RAP file")

# ---------------- Read GRIB ----------------

print("Opening GRIB...")

grbs = pygrib.open(GRIB_FILE)

# ---------------- Auto-detect Tornado Probability ----------------

tornado_msg = None
for msg in grbs:
    # Print available variables (optional, remove if you don't want long output)
    # print(msg)
    if "Tornado" in msg.name or msg.shortName.lower() in ["tor", "torn"]:
        tornado_msg = msg
        break

if tornado_msg is None:
    raise ValueError("No Tornado Probability variable found in GRIB.")

print(f"Using GRIB message: {tornado_msg.name} ({tornado_msg.shortName})")

data = tornado_msg.values
lats, lons = tornado_msg.latlons()

grbs.close()

print("Grid shape:", data.shape)

# ---------------- Normalize ----------------

data = np.clip(data, 0, 1)
data = (data * 100).astype(np.float32)

# ---------------- Raster Bounds ----------------

lat_min = lats.min()
lat_max = lats.max()
lon_min = lons.min()
lon_max = lons.max()

print("Bounds:", lat_min, lat_max, lon_min, lon_max)

# ---------------- Build GeoTIFF ----------------

height, width = data.shape

transform = from_bounds(
    lon_min,
    lat_min,
    lon_max,
    lat_max,
    width,
    height
)

with rasterio.open(
    RASTER_FILE,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=1,
    dtype=data.dtype,
    crs=CRS.from_epsg(4326),
    transform=transform,
) as dst:
    dst.write(data, 1)

print("GeoTIFF created:", RASTER_FILE)

# ---------------- Reproject to Web Mercator ----------------

print("Reprojecting to EPSG:3857...")

if os.path.exists(TMP_MERCATOR):
    os.remove(TMP_MERCATOR)

subprocess.run([
    "gdalwarp",
    "-t_srs", "EPSG:3857",
    "-r", "bilinear",
    "-overwrite",
    RASTER_FILE,
    TMP_MERCATOR
], check=True)

# ---------------- Generate XYZ Tiles ----------------

print("Generating XYZ tiles...")

if os.path.exists(TILE_DIR):
    shutil.rmtree(TILE_DIR)

subprocess.run([
    "gdal2tiles.py",
    "-p", "mercator",
    "-w", "none",
    "--xyz",
    "-z", "3-9",
    TMP_MERCATOR,
    TILE_DIR
], check=True)

# ---------------- Cleanup ----------------

if os.path.exists(TMP_MERCATOR):
    os.remove(TMP_MERCATOR)

print("DONE. Tiles available at:", TILE_DIR)
