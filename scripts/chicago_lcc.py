from pyproj import CRS, Transformer

# Use the exact projection from your LCC JSON
lcc_proj = CRS.from_proj4(
    "+proj=lcc +lat_1=50 +lat_2=50 +lat_0=50 +lon_0=253 +a=6371229 +b=6371229"
)
wgs84 = "EPSG:4326"

transformer = Transformer.from_crs(wgs84, lcc_proj)

# Chicago lat/lon
lat, lon = 41.8781, -87.6298

x, y = transformer.transform(lat, lon)

print("Chicago LCC coordinates:")
print(f"x = {x}")
print(f"y = {y}")
