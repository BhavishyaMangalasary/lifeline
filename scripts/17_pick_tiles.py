"""Draws a fair, seeded sample of tiles we have not used, and prints the commands to run."""
import pandas as pd

ref = pd.read_csv("data/Louisiana-East_Training_Public_reference.csv")
mapping = pd.read_csv("data/Louisiana-East_Training_Public_label_image_mapping.csv")
mapping["ImageId"] = mapping["pre-event image"].str.replace(".tif", "", regex=False)
mapping["row"] = mapping.index

roads = ref[ref["Object"] == "Road"].copy()
roads["flooded"] = roads["Flooded"].astype(str) == "True"
per = roads.groupby("ImageId")["flooded"].agg(flooded="sum", total="count").reset_index()
per = per.merge(mapping[["ImageId", "row"]], on="ImageId")

used = {497, 233, 170, 542, 466, 445, 500, 145, 127, 241, 356}
pool = per[(per["flooded"] >= 5) & (per["total"] >= 20) & (per["total"] <= 120) & (~per["row"].isin(used))]
pick = pool.sample(n=15, random_state=7).sort_values("row")

print(len(pool), "tiles in the pool")
print(pick.to_string(index=False))
rows = " ".join(str(r) for r in pick["row"])
print("\nRun these:")
print(f"for i in {rows}; do python scripts/02_open_tile.py $i > /dev/null; done")
print(f"python scripts/12_eval_decision.py {rows}")