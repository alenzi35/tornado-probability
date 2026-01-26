import cfgrib

grib_path = "data/rap.t20z.awp130pgrbf02.grib2"

# Try opening without filtering to inspect all variables
ds = cfgrib.open_dataset(grib_path, engine="cfgrib", backend_kwargs={'errors':'ignore'})

print("Variables in GRIB:")
for var in ds.variables:
    if var not in ds.dims:
        print(var)
