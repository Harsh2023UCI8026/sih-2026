import pandas as pd
import os
import sys

# Append src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from hydraulic_model import compute_water_depth

# Simplified test for Dwarka Mor using the formula from model_train.py
def compute_depth_for_row(rain_mm, imperv, cap_mmhr, catch_sqm,
                          contributing_fraction=0.15, ponding_area=5000.0):
    runoff = max(0.0, min(1.0, imperv)) * rain_mm
    excess = max(runoff - cap_mmhr, 0.0)
    if excess <= 0:
        return 0.0
    vol = (excess / 1000.0) * catch_sqm * contributing_fraction
    return (vol / ponding_area) * 100.0  # cm

# Dwarka Mor approx params:
# Area: ~1,000,000 sqm
# Cap: ~20 mm/hr
# Imperv: 0.85

print("June 28 2024 (91 mm/hr):", compute_depth_for_row(91.0, 0.85, 20.0, 1_000_000))
print("July 8 2023 (60 mm/hr):", compute_depth_for_row(60.0, 0.85, 20.0, 1_000_000))
print("Aug 20 2023 (40 mm/hr):", compute_depth_for_row(40.0, 0.85, 20.0, 1_000_000))
