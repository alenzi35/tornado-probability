import cfgrib

# Path to your downloaded RAP GRIB
grib_file = "data/rap_latest.grib2"

# Variables and the level ranges you care about
variables = [
    {"shortName": "CAPE", "typeOfLevel": "isobaricInhPa", "min": 0, "max": 90},
    {"shortName": "CIN", "typeOfLevel": "isobaricInhPa", "min": 0, "max": 90},
    {"shortName": "HLCY", "typeOfLevel": "heightAboveGround", "min": 0, "max": 1000},
]

for var in variables:
    try:
        ds = cfgrib.open_dataset(
            grib_file,
            filter_by_keys={"shortName": var["shortName"], "typeOfLevel": var["typeOfLevel"]}
        )
        if len(ds.data_vars) == 0:
            print(f"{var['shortName']} not present in GRIB file.")
        else:
            # Check levels
            levels_name = "isobaricInhPa" if "isobaricInhPa" in var["typeOfLevel"] else "heightAboveGround"
            levels = ds.get(levels_name)
            if levels is not None:
                in_range = any((levels >= var["min"]) & (levels <= var["max"]))
                if in_range:
                    print(f"{var['shortName']} exists in desired level range ({var['min']}-{var['max']}).")
                else:
                    print(f"{var['shortName']} exists but not in desired level range ({var['min']}-{var['max']}).")
            else:
                print(f"{var['shortName']} loaded but levels info not found.")
    except Exception as e:
        print(f"{var['shortName']} could not be read: {e}")
