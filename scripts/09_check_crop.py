import sys

sys.path.insert(0, "src")

import pandas as pd
from PIL import Image

from lifeline.geo.labels import load_tile
from lifeline.perception.muse import crop_piece

i = 497
mapping = pd.read_csv("data/Louisiana-East_Training_Public_label_image_mapping.csv")
image_id = mapping.iloc[i]["pre-event image"].replace(".tif", "")
roads, _ = load_tile(image_id)
post = Image.open(f"out/post_{i}.png").convert("RGB").resize((1300, 1300))

picks = list(roads[roads["flooded"]].index[:2]) + list(roads[~roads["flooded"]].index[:2])
for p in picks:
    crop_piece(post, list(roads.loc[p, "geometry"].coords)).save(f"out/crop_{i}_{p}.png")
    print("piece", p, "flooded (label):", roads.loc[p, "flooded"])