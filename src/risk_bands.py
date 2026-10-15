"""Shared depth-band labels used by model and formula inference paths.

These categories describe estimated depth only. They are not a road-safety
clearance standard and do not imply that the estimate has been validated.
"""

from __future__ import annotations

import math

RISK_BAND_LABELS = (
    "LOW_ESTIMATE",
    "CAUTION",
    "MODERATE",
    "SEVERE",
    "CRITICAL",
)
RISK_BAND_CODES = {label: index for index, label in enumerate(RISK_BAND_LABELS)}


def classify_depth_cm(depth_cm: float) -> str:
    """Classify finite depth in cm into <5, 5–<15, 15–<30, 30–<50, >=50."""
    value = float(depth_cm)
    if not math.isfinite(value):
        raise ValueError("depth_cm must be a finite number")
    value = max(0.0, value)
    if value < 5.0:
        return "LOW_ESTIMATE"
    if value < 15.0:
        return "CAUTION"
    if value < 30.0:
        return "MODERATE"
    if value < 50.0:
        return "SEVERE"
    return "CRITICAL"
