"""Opens one SpaceNet 8 tile and saves a before/after picture."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from PIL import Image

DATA = Path("data")
MAPPING = DATA / "Louisiana-East_Training_Public_label_image_mapping.csv"

def read_rgb(path):
    with rasterio.open(path) as src:
        print(f"{path.name}: {src.width}x{src.height}, {src.count} bands, {src.dtypes[0]}")
        print("   covers:", tuple(round(v, 5) for v in src.bounds))
        arr = src.read([1, 2, 3])
    arr = np.transpose(arr, (1, 2, 0))
    if arr.dtype != np.uint8:
        lo, hi = np.percentile(arr, (2, 98))
        arr = np.clip((arr - lo) / (hi - lo + 1e-9), 0, 1) * 255
    return arr.astype(np.uint8)

def main():
    i = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    row = pd.read_csv(MAPPING).iloc[i]
    print("tile:", row["label"])
    pre = read_rgb(DATA / "PRE-event" / row["pre-event image"])
    post = read_rgb(DATA / "POST-event" / row["post-event image 1"])
    Path("out").mkdir(exist_ok=True)
    Image.fromarray(post).save(f"out/post_{i}.png")
    Image.fromarray(pre).save(f"out/pre_{i}.png")
    post = np.array(Image.fromarray(post).resize((pre.shape[1], pre.shape[0])))
    Image.fromarray(np.hstack([pre, post])).save(f"out/tile_{i}.png")
    print(f"saved out/tile_{i}.png (left = before, right = after)")


if __name__ == "__main__":
    main()
