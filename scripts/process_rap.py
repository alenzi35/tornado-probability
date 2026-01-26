import cfgrib

grib_path = "data/rap.t20z.awp130pgrbf02.grib2"

# List all messages (variables) in the GRIB
from cfgrib import open_fileindex
index = cfgrib.open_fileindex(grib_path)

for i, msg in enumerate(index):
    print(f"{i}: shortName={msg['shortName']}, typeOfLevel={msg['typeOfLevel']}")
