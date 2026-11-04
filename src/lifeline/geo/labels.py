"""Loads one SpaceNet 8 tile's road pieces and buildings from the reference CSV."""
from pathlib import Path

import pandas as pd
from shapely import wkt

DATA = Path("data")
REFERENCE = DATA / "Louisiana-East_Training_Public_reference.csv"

_ref = None


def _reference():
    global _ref
    if _ref is None:
        _ref = pd.read_csv(REFERENCE)
    return _ref

def load_tile(image_id):
    rows = _reference()
    rows = rows[rows["ImageId"] == image_id].copy()
    rows["geometry"] = rows["Wkt_Pix"].apply(wkt.loads)
    rows["flooded"] = rows["Flooded"].astype(str) == "True"
    rows["travel_time_s"] = pd.to_numeric(rows["travel_time_s"], errors="coerce").fillna(60.0)
    rows["length_m"] = pd.to_numeric(rows["length_m"], errors="coerce").fillna(0.0)
    roads = rows[rows["Object"] == "Road"].reset_index(drop=True)
    buildings = rows[rows["Object"] == "Building"].reset_index(drop=True)
    return roads, buildings