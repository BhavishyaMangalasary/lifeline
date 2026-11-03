"""Draws roads and buildings on a tile, coloured by what the flood did to them."""
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

sys.path.insert(0, "src")
from lifeline.geo.access import classify
from lifeline.geo.labels import load_tile

DATA = Path("data")
MAPPING = DATA / "Louisiana-East_Training_Public_label_image_mapping.csv"
COLORS = {
    "isolated": (255, 140, 0),
    "ok": (40, 120, 255),
    "no_road": (200, 200, 200),
    "unconnected": (200, 200, 200),
}

def draw_tile(i):
    row = pd.read_csv(MAPPING).iloc[i]
    image_id = row["pre-event image"].replace(".tif", "")
    roads, buildings = load_tile(image_id)
    result = classify(roads, buildings)

    base = Image.open(f"out/post_{i}.png").convert("RGBA").resize((1300, 1300))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _, r in roads.iterrows():
        color = (255, 40, 40, 255) if r["flooded"] else (60, 220, 90, 255)
        d.line(list(r["geometry"].coords), fill=color, width=5)
    for _, b in result.iterrows():
        c = COLORS[b["status"]]
        d.polygon(list(b["geometry"].exterior.coords), fill=c + (130,), outline=c + (255,))
    return Image.alpha_composite(base, layer).convert("RGB"), result

def main():
    i = int(sys.argv[1]) if len(sys.argv) > 1 else 497
    img, result = draw_tile(i)
    img.save(f"out/plan_{i}.png")
    print(result["status"].value_counts())
    print(f"saved out/plan_{i}.png")


if __name__ == "__main__":
    main()