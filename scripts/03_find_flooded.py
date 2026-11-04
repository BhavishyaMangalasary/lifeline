"""Finds tiles with the most flooded roads, so we can pick good demo tiles."""
from pathlib import Path

import pandas as pd

DATA = Path("data")
ref = pd.read_csv(DATA / "Louisiana-East_Training_Public_reference.csv")
mapping = pd.read_csv(DATA / "Louisiana-East_Training_Public_label_image_mapping.csv")

print(ref.groupby(["Object", "Flooded"], dropna=False).size())

roads = ref[ref["Object"] == "Road"].copy()
roads["flooded"] = roads["Flooded"].astype(str) == "True"
per_tile = roads.groupby("ImageId")["flooded"].agg(flooded_roads="sum", total_roads="count").reset_index()

mapping["ImageId"] = mapping["pre-event image"].str.replace(".tif", "", regex=False)
mapping["row"] = mapping.index
best = per_tile.merge(mapping[["ImageId", "row"]], on="ImageId")
best = best.sort_values("flooded_roads", ascending=False)
print()
print(best.head(10).to_string(index=False))

best["dry_roads"] = best["total_roads"] - best["flooded_roads"]
mixed = best[(best["flooded_roads"] >= 15) & (best["dry_roads"] >= 15)]
print()
print(mixed.sort_values("dry_roads", ascending=False).head(10).to_string(index=False))