for var in VARIABLES:
    try:
        # Attempt to open dataset with filter
        ds_var = xr.open_dataset(local_file, engine="cfgrib",
                                 filter_by_keys=var)
        if len(ds_var.data_vars) == 0:
            print(f"Warning: {var['shortName']} not in this GRIB file")
            continue
        name = list(ds_var.data_vars)[0]
        data_dict[var["shortName"]] = ds_var[name].values
        print(f"Loaded {var['shortName']} ({var['typeOfLevel']})")
    except Exception as e:
        print(f"Failed to load {var['shortName']}: {e}")
