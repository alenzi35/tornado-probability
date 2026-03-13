import pygrib
import sys

# ================= CONFIG =================
# ← Change this to the actual path of your GRIB2 file
GRIB_PATH = "https://noaa-rap-pds.s3.amazonaws.com/rap.{DATE}/rap.t{HOUR}z.awip32f{FCST}.grib2"

try:
    grbs = pygrib.open(GRIB_PATH)
except Exception as e:
    print(f"Failed to open GRIB2 file: {e}")
    sys.exit(1)

print(f"\nInspecting GRIB2 file: {GRIB_PATH}\n")
print(f"{'Idx':>3} | {'shortName':<12} | {'name':<35} | {'typeOfLevel':<20} | level(s)\n" 
      + "-"*100)

for i, g in enumerate(grbs, start=1):
    # build a simple string for level info
    level_info = ""
    if hasattr(g, "level"):
        level_info = f"lvl={g.level}"
    if hasattr(g, "bottomLevel") and hasattr(g, "topLevel"):
        level_info = f"bot={g.bottomLevel}, top={g.topLevel}"

    print(f"{i:3d} | {g.shortName:<12} | {g.name:<35} | {g.typeOfLevel:<20} | {level_info}")

grbs.close()
print("\nDone.\n")
