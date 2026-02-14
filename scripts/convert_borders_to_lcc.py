import geopandas as gpd
import json
from pyproj import CRS


# Load shapefile
shp_path = "ne_50m_admin_1_states_provinces.shp"

gdf = gpd.read_file(shp_path)


# RAP Lambert Conformal projection
lcc = CRS.from_proj4("""
+proj=lcc
+lat_1=50
+lat_2=50
+lat_0=50
+lon_0=253
+a=6371229
+b=6371229
+units=m
+no_defs
""")


# Reproject
gdf = gdf.to_crs(lcc)


lines = []


for _, row in gdf.iterrows():

    geom = row.geometry

    if geom is None:
        continue


    if geom.geom_type == "MultiLineString":

        for part in geom.geoms:
            lines.append(list(part.coords))


    elif geom.geom_type == "LineString":

        lines.append(list(geom.coords))


# Save
out = {
    "projection": "LCC",
    "borders": lines
}


with open("map/data/borders_lcc.json", "w") as f:
    json.dump(out, f)


print("Saved map/data/borders_lcc.json")
print("Lines:", len(lines))
