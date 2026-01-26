import xarray as xr

def find_variable_in_grib(grib_path, var_name, level_candidates):
    """Return the dataset and variable values once we find it."""
    for level in level_candidates:
        try:
            ds = xr.open_dataset(grib_path, engine="cfgrib",
                                 filter_by_keys={"typeOfLevel": level})
            if var_name in ds:
                print(f"{var_name} ✅ FOUND at {level}")
                return ds[var_name].values
        except Exception:
            continue
    raise RuntimeError(f"{var_name} NOT FOUND in any candidate level types!")

grib_path = "data/rap.t20z.awp130pgrbf02.grib2"
level_candidates = [
    "atmosphereSingleLayer",
    "surface",
    "isobaricInhPa",
    "atmosphere"
]

cape = find_variable_in_grib(grib_path, "CAPE", level_candidates)
cin  = find_variable_in_grib(grib_path, "CIN", level_candidates)
hlcy = find_variable_in_grib(grib_path, "HLCY", ["heightAboveGround"])
