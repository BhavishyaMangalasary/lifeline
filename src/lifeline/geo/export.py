"""Turns one tile's results into GeoJSON on a real map (longitude / latitude)."""
import json
from pathlib import Path

import pandas as pd
import rasterio
from PIL import Image
from shapely.affinity import affine_transform
from shapely.geometry import Point, mapping

from lifeline.geo.access import classify, classify_uncertain, dispatch
from lifeline.geo.labels import load_tile
from lifeline.perception.muse import perceive_tile

DATA = Path("data")
MAPPING = DATA / "Louisiana-East_Training_Public_label_image_mapping.csv"


def _to_lonlat(geom, t):
    """t is the photo's pixel-to-map transform; this moves a shape onto the real map."""
    return affine_transform(geom, [t.a, t.b, t.d, t.e, t.c, t.f])


def _feature(geom, props):
    return {"type": "Feature", "geometry": mapping(geom), "properties": props}

def build_tile(i):
    row = pd.read_csv(MAPPING).iloc[i]
    pre_name = row["pre-event image"]
    image_id = pre_name.replace(".tif", "")
    with rasterio.open(DATA / "PRE-event" / pre_name) as src:
        t = src.transform
        b = src.bounds
    roads, buildings = load_tile(image_id)
    post = Image.open(f"out/post_{i}.png").convert("RGB").resize((1300, 1300))
    pre = Image.open(f"out/pre_{i}.png").convert("RGB").resize((1300, 1300))

    truth = classify(roads, buildings)
    states = perceive_tile(pre, post, roads)
    pred = classify_uncertain(roads, buildings, states)

    perceived = roads.copy()
    perceived["flooded"] = [s == "flooded" for s in states]
    groups, _ = dispatch(perceived, classify(perceived, buildings))

    features = []
    for k, r in roads.iterrows():
        features.append(_feature(_to_lonlat(r["geometry"], t), {
            "kind": "road",
            "state": states[k],
            "label_flooded": bool(r["flooded"]),
            "length_m": round(float(r["length_m"]), 1),
        }))
    for k, bd in buildings.iterrows():
        features.append(_feature(_to_lonlat(bd["geometry"], t), {
            "kind": "building",
            "status": str(pred.loc[k, "status"]),
            "truth": str(truth.loc[k, "status"]),
        }))
    for rank, g in groups.iterrows():
        features.append(_feature(_to_lonlat(Point(g["entry"]), t), {
            "kind": "entry",
            "rank": int(rank) + 1,
            "buildings": int(g["buildings"]),
            "eta_s": round(float(g["eta_s"]), 1),
        }))

    summary = {
        "tile": int(i),
        "image_id": image_id,
        "bounds": [round(v, 6) for v in (b.left, b.bottom, b.right, b.top)],
        "road_pieces": int(len(roads)),
        "roads_flooded": int(sum(s == "flooded" for s in states)),
        "roads_uncertain": int(sum(s == "uncertain" for s in states)),
        "buildings": {k: int(v) for k, v in pred["status"].value_counts().items()},
        "buildings_truth": {k: int(v) for k, v in truth["status"].value_counts().items()},
    }
    return {"type": "FeatureCollection", "features": features, "summary": summary}


def write_tile(i):
    out = Path("app/data")
    out.mkdir(parents=True, exist_ok=True)
    data = build_tile(i)
    (out / f"tile_{i}.geojson").write_text(json.dumps(data))
    return data["summary"]

