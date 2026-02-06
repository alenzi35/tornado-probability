import os
import json
import shutil
import subprocess
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

# ---------------- Paths ----------------
DATA_DIR = "map/data"
MAP_DIR = "map"
TILE_DIR = "map/tiles"

JSON_FILE = os.path.join(DATA_DIR, "tornado_prob.json")
RASTER_FILE = os.path.join(MAP_DIR, "output.tif")
TMP_MERCATOR = os.path.join(MAP_DIR, "output_3857.tif")

# ---------------- Setup ----------------
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)

print("Starting RAP processing from JSON...")

# ---------------- Load JSON ----------------
with open(JSON_FILE, "r") as f:
    cells = json.load(f)

if not cells:
    raise ValueError("JSON is empty")

print(f"Loaded {len(cells)} cells")

# ---------------- Determine raster bounds ----------------
lat_mins = [c["lat_min"] for c in cells]
lat_maxs = [c["lat_max"] for c in cells]
lon_mins = [c["lon_min"] for c in cells]
lon_maxs = [c["lon_max"] for c in cells]

lat_min = min(lat_mins)
lat_max = max(lat_maxs)
lon_min = min(lon_mins)
lon_max = max(lon_maxs)

# ---------------- Raster resolution ----------------
lat_res = cells[0]["lat_max"] - cells[0]["lat_min"]
lon_res = cells[0]["lon_max"] - cells[0]["lon_min"]

n_rows = int(np.ceil((lat_max - lat_min) / lat_res))
n_cols = int(np.ceil((lon_max - lon_min) / lon_res))

print(f"Raster size: {n_cols} cols x {n_rows} rows")

# ---------------- Build empty raster ----------------
raster = np.zeros((n_rows, n_cols), dtype=np.float32)

# ---------------- Fill raster ----------------
for cell in cells:
    row = int((lat_max - cell["lat_max"]) / lat_res)
    col = int((cell["lon_min"] - lon_min) / lon_res)
    if 0 <= row < n_rows and 0 <= col < n_cols:
        raster[row, col] = cell["prob"] * 100  # 0–100

# ---------------- Create GeoTIFF ----------------
transform = from_bounds(lon_min, lat_min, lon_max, lat_max, n_cols, n_rows)

with rasterio.open(
    RASTER_FILE,
    "w",
    driver="GTiff",
    height=n_rows,
    width=n_cols,
    count=1,
    dtype=raster.dtype,
    crs=CRS.from_epsg(4326),
    transform=transform
) as dst:
    dst.write(raster, 1)

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

# ---------------- Scale to 8-bit for gdal2tiles ----------------
TEMP_BYTE = TMP_MERCATOR.replace(".tif", "_byte.tif")

subprocess.run([
    "gdal_translate",
    "-of", "VRT",
    "-ot", "Byte",
    "-scale", "0", "100", "0", "255",
    TMP_MERCATOR,
    TEMP_BYTE + ".vrt"
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
    TEMP_BYTE + ".vrt",
    TILE_DIR
], check=True)

# ---------------- Cleanup ----------------
os.remove(TEMP_BYTE + ".vrt")
if os.path.exists(TMP_MERCATOR):
    os.remove(TMP_MERCATOR)

print("DONE. Tiles are available at:", TILE_DIR)
