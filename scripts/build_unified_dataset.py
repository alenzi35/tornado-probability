import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

# ================= FILE PATHS =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root

TORNADO_CSV = os.path.join(BASE_DIR, "map", "data", "1hr_samples.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "map", "data", "rap_unified_dataset.json")

# ================= LOAD CSV =================
print("Loading tornado CSV:", TORNADO_CSV)

tor_df = pd.read_csv(TORNADO_CSV)

print(f"Loaded {len(tor_df)} samples.")
# ... rest of your dataset processing code remains the same ...
